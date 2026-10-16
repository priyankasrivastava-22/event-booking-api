"""Venue setup and public seating read API.

All reservations MUST go through /api/bookings + InventoryService; the
original SeatLock-only checkout route bypassed BookingItem inventory and was
not compatible with the unified booking/payment path.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

import models
import schemas_seating
from utils.helpers import get_db
from core.security import get_current_user

router = APIRouter()


def require_admin(user):
    role = user.get("role") if isinstance(user, dict) else getattr(user, "role", None)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


def _event(db, event_id):
    event = db.get(models.Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def _zone(db, zone_id):
    zone = db.get(models.EventZone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


def _zone_output(zone):
    return {
        "id": zone.id, "event_id": zone.event_id, "layout_id": zone.layout_id,
        "name": zone.name, "code": zone.code, "zone_type": zone.zone_type,
        "capacity": zone.capacity, "base_price": zone.base_price,
        "sold_count": zone.sold_count, "locked_count": zone.locked_count,
        "available": max(0, zone.capacity - zone.sold_count - zone.locked_count),
        "is_active": zone.is_active,
    }


@router.get("/admin/events/{event_id}/layout")
def get_layout(event_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_admin(user)
    _event(db, event_id)
    layout = (db.query(models.VenueLayout)
              .filter_by(event_id=event_id, is_active=True).first())
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not configured")
    return layout


@router.post("/admin/events/{event_id}/layout", status_code=201)
def create_layout(event_id: int, data: schemas_seating.LayoutCreate,
                  db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_admin(user)
    _event(db, event_id)
    if data.event_id != event_id:
        raise HTTPException(status_code=400, detail="Event ID mismatch")
    if db.query(models.VenueLayout.id).filter_by(event_id=event_id, is_active=True).first():
        raise HTTPException(status_code=409, detail="Event already has an active layout")
    layout = models.VenueLayout(event_id=event_id, name=data.name.strip())
    db.add(layout)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Layout already exists")
    db.refresh(layout)
    return layout


@router.get("/admin/layouts/{layout_id}/zones")
def list_zones(layout_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_admin(user)
    if not db.get(models.VenueLayout, layout_id):
        raise HTTPException(status_code=404, detail="Layout not found")
    return [_zone_output(z) for z in db.query(models.EventZone)
            .filter_by(layout_id=layout_id).order_by(models.EventZone.id).all()]


@router.post("/admin/layouts/{layout_id}/zones", status_code=201)
def create_zone(layout_id: int, data: schemas_seating.ZoneCreate,
                db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_admin(user)
    layout = db.get(models.VenueLayout, layout_id)
    if not layout or not layout.is_active:
        raise HTTPException(status_code=404, detail="Active layout not found")
    event = _event(db, layout.event_id)
    expected = "seated" if event.inventory_type == models.INVENTORY_SEAT else "general"
    if event.inventory_type == models.INVENTORY_GENERAL:
        raise HTTPException(status_code=400, detail="General-admission events use ticket types, not zones")
    if data.zone_type != expected:
        raise HTTPException(status_code=400, detail=f"This event requires {expected} zones")
    code = data.code.strip().upper()
    if db.query(models.EventZone.id).filter_by(event_id=event.id, code=code).first():
        raise HTTPException(status_code=409, detail="Zone code already exists")
    zone = models.EventZone(event_id=event.id, layout_id=layout.id,
                            name=data.name.strip(), code=code, zone_type=expected,
                            capacity=data.capacity, base_price=data.base_price)
    db.add(zone)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Zone already exists")
    db.refresh(zone)
    return _zone_output(zone)


@router.get("/admin/zones/{zone_id}/rows")
def list_rows(zone_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_admin(user)
    _zone(db, zone_id)
    rows = (db.query(models.VenueRow).filter_by(zone_id=zone_id)
            .order_by(models.VenueRow.row_number).all())
    return [{"id": row.id, "row_label": row.row_label, "row_number": row.row_number,
             "seats": [{"id": seat.id, "seat_code": seat.seat_code,
                        "seat_number": seat.seat_number, "status": seat.status,
                        "price": seat.price, "is_active": seat.is_active}
                       for seat in sorted(row.seats, key=lambda s: s.seat_number)]}
            for row in rows]


@router.post("/admin/zones/{zone_id}/rows", status_code=201)
def create_row(zone_id: int, data: schemas_seating.RowCreate,
               db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_admin(user)
    zone = db.query(models.EventZone).filter_by(id=zone_id).with_for_update().first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    if data.zone_id != zone_id:
        raise HTTPException(status_code=400, detail="Zone ID mismatch")
    if zone.zone_type != "seated" or not zone.is_active:
        raise HTTPException(status_code=400, detail="Rows require an active seated zone")
    label = data.row_label.strip().upper()
    if db.query(models.VenueRow.id).filter_by(zone_id=zone_id, row_label=label).first():
        raise HTTPException(status_code=409, detail="Row already exists")
    existing = db.query(func.count(models.Seat.id)).filter_by(zone_id=zone_id).scalar() or 0
    if zone.capacity and existing + data.seat_count > zone.capacity:
        raise HTTPException(status_code=400, detail=f"Only {max(0, zone.capacity - existing)} seats remain in this zone")
    next_number = (db.query(func.max(models.VenueRow.row_number))
                   .filter_by(zone_id=zone_id).scalar() or 0) + 1
    row = models.VenueRow(event_id=zone.event_id, zone_id=zone.id,
                          row_label=label, row_number=next_number)
    try:
        db.add(row)
        db.flush()
        price = data.starting_price if data.starting_price else zone.base_price
        for n in range(1, data.seat_count + 1):
            seat = models.Seat(event_id=zone.event_id, zone_id=zone.id,
                               row_id=row.id, seat_number=n,
                               seat_code=f"{zone.code}-{label}-{n}", price=price)
            db.add(seat)
            db.flush()
            db.add(models.Inventory(event_id=zone.event_id,
                                    inventory_type=models.INVENTORY_SEAT,
                                    status=models.INVENTORY_AVAILABLE,
                                    seat_id=seat.id, zone_id=zone.id, price=price))
        if zone.capacity == 0:
            zone.capacity = existing + data.seat_count
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Row or seat identifier already exists")
    return {"success": True, "row_id": row.id, "row_label": label,
            "seats_created": data.seat_count}


@router.delete("/admin/zones/{zone_id}")
def delete_zone(zone_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_admin(user)
    zone = _zone(db, zone_id)
    if zone.sold_count or zone.locked_count:
        raise HTTPException(status_code=409, detail="Cannot delete a zone with active holds or sales")
    if db.query(models.Ticket.id).filter_by(zone_id=zone_id).first():
        raise HTTPException(status_code=409, detail="This zone has issued tickets")
    inventory_ids = [inv.id for inv in zone.inventories]
    if inventory_ids and db.query(models.BookingItem.id).filter(models.BookingItem.inventory_id.in_(inventory_ids)).first():
        raise HTTPException(status_code=409, detail="Zone has booking history")
    try:
        # Flush Inventory separately to satisfy RESTRICT relations while removing unused zones.
        for inv in list(zone.inventories):
            db.delete(inv)
        db.delete(zone)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Zone is referenced by existing booking data")
    return {"message": "deleted"}


@router.get("/events/{event_id}/seats")
def get_event_seats(event_id: int, db: Session = Depends(get_db)):
    event = _event(db, event_id)
    if event.inventory_type != models.INVENTORY_SEAT:
        raise HTTPException(status_code=400, detail="Event does not use fixed seating")
    rows = (db.query(models.Seat).filter_by(event_id=event_id, is_active=True)
            .order_by(models.Seat.zone_id, models.Seat.row_id, models.Seat.seat_number).all())
    now = datetime.now(timezone.utc)
    def visible_status(seat):
        inv = seat.inventory
        if (inv and inv.status == models.INVENTORY_LOCKED and inv.locked_until
                and inv.locked_until.replace(tzinfo=inv.locked_until.tzinfo or timezone.utc) <= now):
            return models.SEAT_AVAILABLE
        return seat.status

    return [{"id": s.id, "seat_code": s.seat_code, "seat_number": s.seat_number,
             "zone_id": s.zone_id, "zone_name": s.zone.name,
             "row_label": s.row.row_label, "status": visible_status(s), "price": s.price}
            for s in rows]


@router.post("/events/{event_id}/seats/lock", status_code=410)
def deprecated_seat_lock(event_id: int, user=Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="Use POST /api/bookings with seat_ids for an atomic booking hold")


@router.post("/events/{event_id}/seats/confirm", status_code=410)
def deprecated_seat_confirm(event_id: int, user=Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="Use POST /api/payment/ to complete a held booking")
