from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from datetime import datetime, timezone
import cloudinary.uploader
from core.cloudinary_config import cloudinary
from sqlalchemy.orm import Session
import models, schemas
from utils.helpers import get_db
from core.security import get_current_user

router = APIRouter()


def admin_check(user):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


@router.post("/{event_id}/ticket-types", response_model=schemas.TicketTypeResponse)
def create_ticket_type(
    event_id: int,
    ticket_type: schemas.TicketTypeCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)

    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.inventory_type != models.INVENTORY_GENERAL:
        raise HTTPException(status_code=400, detail="Only general-admission events accept pass ticket types")
    db_ticket_type = models.TicketType(
        event_id=event_id,
        zone_id=ticket_type.zone_id,
        name=ticket_type.name,
        price=ticket_type.price,
        inventory_limit=ticket_type.inventory_limit,   # None = unlimited
        is_active=True,
    )

    db.add(db_ticket_type)
    db.commit()
    db.refresh(db_ticket_type)

    return db_ticket_type


@router.get("/{event_id}/ticket-types", response_model=list[schemas.TicketTypeResponse])
def list_ticket_types(event_id: int, db: Session = Depends(get_db)):
    return db.query(models.TicketType).filter(
        models.TicketType.event_id == event_id,
        models.TicketType.is_active == True
    ).all()


@router.delete("/ticket-types/{ticket_type_id}")
def delete_ticket_type(
    ticket_type_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)

    ticket_type = db.query(models.TicketType).filter(models.TicketType.id == ticket_type_id).first()
    if not ticket_type:
        raise HTTPException(status_code=404, detail="Ticket type not found")

    if ticket_type.sold_count or ticket_type.locked_count:
        raise HTTPException(status_code=409, detail="Cannot delete a ticket type with holds or sales")
    if ticket_type.inventory and ticket_type.inventory.booking_items:
        raise HTTPException(status_code=409, detail="Ticket type has booking history")
    db.delete(ticket_type)
    db.commit()
    return {"message": "deleted"}


def _build_seat_inventory(db: Session, event: models.Event) -> dict:
    """FIXED_SEAT event: active layout + zones, each with a flat seat list
    (row_label/row_number denormalized onto every seat). Matches exactly
    what event-details.js's flattenSeats()/groupSeatsByRow() expect -
    zone.seats (flat), not zone.rows[].seats (nested)."""
    layout = (
        db.query(models.VenueLayout)
        .filter(models.VenueLayout.event_id == event.id, models.VenueLayout.is_active == True)
        .first()
    )

    zones = (
        db.query(models.EventZone)
        .filter(models.EventZone.event_id == event.id, models.EventZone.is_active == True)
        .all()
    )

    zones_out = []
    for zone in zones:
        rows = (
            db.query(models.VenueRow)
            .filter(models.VenueRow.zone_id == zone.id)
            .order_by(models.VenueRow.row_number)
            .all()
        )
        seats_out = []
        for row in rows:
            seats = (
                db.query(models.Seat)
                .filter(models.Seat.row_id == row.id, models.Seat.is_active == True)
                .order_by(models.Seat.seat_number)
                .all()
            )
            for seat in seats:
                seats_out.append({
                    "id": seat.id,
                    "seat_code": seat.seat_code,
                    "seat_number": seat.seat_number,
                    "row_label": row.row_label,
                    "row_number": row.row_number,
                    "zone_id": zone.id,
                    "zone_name": zone.name,
                    "zone_code": zone.code,
                    "status": (models.SEAT_AVAILABLE
                               if seat.inventory and seat.inventory.status == models.INVENTORY_LOCKED
                               and seat.inventory.locked_until
                               and seat.inventory.locked_until.replace(tzinfo=seat.inventory.locked_until.tzinfo or timezone.utc) <= datetime.now(timezone.utc)
                               else seat.status),
                    "price": seat.price,
                })
        zones_out.append({
            "id": zone.id,
            "name": zone.name,
            "code": zone.code,
            "base_price": zone.base_price,
            "seats": seats_out,
        })

    return {
        "layout": {"id": layout.id, "name": layout.name, "version": layout.version} if layout else None,
        "zones": zones_out,
    }


def _build_zone_inventory(db: Session, event: models.Event) -> list:
    """ZONE event: pooled zones with live availability (capacity - sold - locked)."""
    zones = (
        db.query(models.EventZone)
        .filter(models.EventZone.event_id == event.id, models.EventZone.is_active == True)
        .all()
    )
    return [
        {
            "id": zone.id,
            "name": zone.name,
            "code": zone.code,
            "base_price": zone.base_price,
            "capacity": zone.capacity,
            "available": max(0, zone.capacity - zone.sold_count - zone.locked_count),
        }
        for zone in zones
    ]


def _build_general_inventory(db: Session, event: models.Event) -> list:
    """GENERAL/PASS event: pooled ticket types with live availability."""
    ticket_types = (
        db.query(models.TicketType)
        .filter(models.TicketType.event_id == event.id, models.TicketType.is_active == True)
        .all()
    )
    return [
        {
            "id": tt.id,
            "name": tt.name,
            "price": tt.price,
            "inventory_limit": tt.inventory_limit,
            "available": (
                max(0, tt.inventory_limit - tt.sold_count - tt.locked_count)
                if tt.inventory_limit is not None
                else None  # unlimited
            ),
        }
        for tt in ticket_types
    ]


def _ensure_ready_to_publish(db: Session, event: models.Event):
    """A public event needs configured inventory before customers may pay."""
    if event.inventory_type == models.INVENTORY_SEAT:
        ready = db.query(models.Seat.id).filter_by(event_id=event.id, is_active=True).first()
    elif event.inventory_type == models.INVENTORY_ZONE:
        ready = db.query(models.EventZone.id).filter(
            models.EventZone.event_id == event.id, models.EventZone.is_active.is_(True),
            models.EventZone.capacity > 0).first()
    else:
        ready = db.query(models.TicketType.id).filter(
            models.TicketType.event_id == event.id, models.TicketType.is_active.is_(True)).first()
    if not ready:
        raise HTTPException(status_code=409, detail="Configure seats, zones or ticket types before publishing")


def _public_event(event: models.Event, db: Session) -> dict:
    """Event card values come from sellable inventory, never legacy counters."""
    if event.inventory_type == models.INVENTORY_SEAT:
        seating = _build_seat_inventory(db, event)
        seats = [s for z in seating["zones"] for s in z["seats"]]
        total = len(seats)
        available = sum(s["status"] == models.SEAT_AVAILABLE for s in seats)
        prices = [s["price"] for s in seats if s["status"] == models.SEAT_AVAILABLE]
        prices = prices or [s["price"] for s in seats]
    elif event.inventory_type == models.INVENTORY_ZONE:
        zones = _build_zone_inventory(db, event)
        total = sum(z["capacity"] for z in zones)
        available = sum(z["available"] for z in zones)
        prices = [z["base_price"] for z in zones if z["available"] > 0]
        prices = prices or [z["base_price"] for z in zones]
    else:
        kinds = _build_general_inventory(db, event)
        total = (sum(k["inventory_limit"] for k in kinds if k["inventory_limit"] is not None)
                 if all(k["inventory_limit"] is not None for k in kinds) else None)
        available = (sum(k["available"] for k in kinds)
                     if all(k["available"] is not None for k in kinds) else None)
        prices = [k["price"] for k in kinds if k["available"] is None or k["available"] > 0]
        prices = prices or [k["price"] for k in kinds]
    return {
        "id": event.id, "title": event.title, "location": event.location,
        "description": event.description, "date_time": event.date_time,
        "price": min(prices) if prices else event.price,
        "image_url": event.image_url, "category": event.category,
        "category_id": event.category_id, "total_seats": total,
        "available_seats": available, "inventory_type": event.inventory_type,
        "age_limit": event.age_limit, "duration": event.duration,
        "status": event.status,
    }


@router.post("/", response_model=schemas.EventResponse)
def create_event(
    event: schemas.EventCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)

    category_id = None
    category_name = None

    # NEW SYSTEM
    if event.category_id:
        category = db.query(models.Category).filter(
            models.Category.id == event.category_id
        ).first()

        if not category:
            raise HTTPException(status_code=400, detail="Invalid category_id")

        category_id = category.id
        category_name = category.name

    # OLD SYSTEM (fallback)
    elif event.category:
        category_name = event.category

    db_event = models.Event(
        title=event.title,
        location=event.location,
        description=event.description,
        date_time=event.date_time,
        price=event.price,
        image_url=event.image_url,
        total_seats=event.total_seats,
        available_seats=event.total_seats,
        category=category_name,
        category_id=category_id,
        age_limit = event.age_limit or "All Ages",
        duration = event.duration,
        status="draft",  # Set up inventory first; publish through PUT after validation.
        inventory_type=event.inventory_type,
    )

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    return db_event


@router.get("/")
def get_events(
    page: int = 1,
    limit: int = 16,

    # SEARCH
    title: str = None,

    # FILTERS
    category: str = None,
    date: str = None,
    min_price: int = None,
    max_price: int = None,

    db: Session = Depends(get_db)
):
    query = db.query(models.Event).filter(models.Event.status == "published")

    # SEARCH BY TITLE
    if title:
        query = query.filter(models.Event.title.ilike(f"%{title}%"))

    # FILTER BY CATEGORY (NEW)
    if category:
        query = query.filter(models.Event.category.ilike(category))

    # FILTER BY DATE
    if date:
        query = query.filter(models.Event.date_time == date)

    # Price filters apply to actual sellable inventory pricing, not the stale
    # legacy Event.price column. For large catalogs replace this with a joined
    # aggregate query and SQL pagination.
    results = [_public_event(e, db) for e in query.order_by(models.Event.id.desc()).all()]
    if min_price is not None:
        results = [e for e in results if e["price"] >= min_price]
    if max_price is not None:
        results = [e for e in results if e["price"] <= max_price]
    skip = (max(1, page) - 1) * max(1, min(limit, 100))
    return results[skip : skip + max(1, min(limit, 100))]


@router.get("/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Every field event-details.js already reads stays exactly as it was -
    # this is purely additive, nothing here changes existing behavior.
    response = _public_event(event, db)

    # Additive per-type structure so the frontend can eventually branch on
    # inventory_type. Uses the same "seat"/"zone"/"general" values already
    # defined in models.py - no separate label scheme to keep in sync.
    if event.inventory_type == models.INVENTORY_SEAT:
        response["seating"] = _build_seat_inventory(db, event)
    elif event.inventory_type == models.INVENTORY_ZONE:
        response["zones"] = _build_zone_inventory(db, event)
    else:
        # models.INVENTORY_GENERAL, or any legacy event with no seating/zone
        # setup at all - returns an empty list, which is fine: those events
        # still work off the flat price/available_seats fields above.
        response["ticket_types"] = _build_general_inventory(db, event)

    return response


@router.get("/{event_id}/inventory")
def get_event_inventory_detail(event_id: int, db: Session = Depends(get_db)):
    """Dedicated inventory endpoint - event-details.js calls this separately
    from GET /{event_id}. Reuses the exact same builders so the two never
    drift out of sync with each other."""
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    response = {"inventory_type": event.inventory_type}

    if event.inventory_type == models.INVENTORY_SEAT:
        seating = _build_seat_inventory(db, event)
        # Flatten to a plain seat list too, since the frontend's flattenSeats()
        # already knows how to read data.zones[].seats - this shape covers it.
        response["zones"] = seating["zones"]
        response["layout"] = seating["layout"]
    elif event.inventory_type == models.INVENTORY_ZONE:
        response["zones"] = _build_zone_inventory(db, event)
    else:
        response["ticket_types"] = _build_general_inventory(db, event)

    return response


@router.put("/{event_id}")
def update_event(
    event_id: int,
    data: schemas.EventUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)

    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if data.inventory_type and data.inventory_type != event.inventory_type:
        configured = (db.query(models.Seat.id).filter_by(event_id=event_id).first()
                      or db.query(models.EventZone.id).filter_by(event_id=event_id).first()
                      or db.query(models.TicketType.id).filter_by(event_id=event_id).first()
                      or db.query(models.Booking.id).filter_by(event_id=event_id).first())
        if configured:
            raise HTTPException(status_code=409, detail="Cannot change inventory type after seating, tickets or bookings exist")
        event.inventory_type = data.inventory_type
    fields = ["title", "location", "price", "image_url", "description", "date_time"]
    if event.inventory_type == models.INVENTORY_GENERAL:
        fields.extend(["total_seats", "available_seats"])
    for key in fields:
        value = getattr(data, key)
        if value is not None:
            setattr(event, key, value)
    if data.age_limit is not None:
        event.age_limit = data.age_limit
    if data.status is not None:
        if data.status == "published" and event.status != "published":
            _ensure_ready_to_publish(db, event)
        event.status = data.status
    if data.duration is not None:
        event.duration = data.duration
        # handle category update safely
    if data.category_id:
        category = db.query(models.Category).filter(
            models.Category.id == data.category_id
        ).first()

        if not category:
            raise HTTPException(status_code=400, detail="Invalid category_id")

        event.category_id = category.id
        event.category = category.name

    elif data.category:
        event.category = data.category

    db.commit()
    return event


@router.delete("/{event_id}")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)

    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db.delete(event)
    db.commit()
    return {"message": "deleted"}


# ---------------- UPLOAD EVENT IMAGE ----------------
@router.post("/{event_id}/upload-image")
def upload_event_image(
    event_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    admin_check(user)
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    result = cloudinary.uploader.upload(
        file.file,
        folder="event_images",
        transformation=[{"width": 1200, "height": 675, "crop": "fill"}]
    )

    event.image_url = result["secure_url"]
    db.commit()
    db.refresh(event)

    return {"message": "Image uploaded", "image_url": event.image_url}

@router.get("/admin/list")                                                                                               # ADMIN EVENTS LIST — with total count for pagination
def get_events_admin(
    page: int = 1,
    limit: int = 10,
    title: str = None,
    category: str = None,
    status: str = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)

    query = db.query(models.Event)

    if title:
        query = query.filter(models.Event.title.ilike(f"%{title}%"))
    if category:
        query = query.filter(models.Event.category.ilike(category))
    if status:
        query = query.filter(models.Event.status == status)

    total = query.count()
    skip = (page - 1) * limit
    events = query.order_by(models.Event.id.desc()).offset(skip).limit(limit).all()

    return {
        "items": [_public_event(e, db) for e in events],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": max(1, (total + limit - 1) // limit)
    }


@router.post("/{event_id}/duplicate", response_model=schemas.EventResponse)                                              # DUPLICATE EVENT
def duplicate_event(
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)

    original = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Event not found")

    copy = models.Event(
        title=f"{original.title} (Copy)",
        location=original.location,
        description=original.description,
        date_time=original.date_time,
        price=original.price,
        image_url=original.image_url,
        total_seats=original.total_seats,
        available_seats=original.total_seats,
        category=original.category,
        category_id=original.category_id,
        age_limit=original.age_limit,
        duration=original.duration,
        status="draft",
        inventory_type=original.inventory_type,
    )

    db.add(copy)
    db.commit()
    db.refresh(copy)
    return copy