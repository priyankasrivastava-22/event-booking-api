from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
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
                    "status": seat.status,
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
        category_id=category_id
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
    query = db.query(models.Event)

    # SEARCH BY TITLE
    if title:
        query = query.filter(models.Event.title.ilike(f"%{title}%"))

    # FILTER BY CATEGORY (NEW)
    if category:
        query = query.filter(models.Event.category.ilike(category))

    # FILTER BY DATE
    if date:
        query = query.filter(models.Event.date_time == date)

    # FILTER BY PRICE
    if min_price is not None:
        query = query.filter(models.Event.price >= min_price)

    if max_price is not None:
        query = query.filter(models.Event.price <= max_price)

    # PAGINATION
    skip = (page - 1) * limit
    events = query.offset(skip).limit(limit).all()

    return events

@router.get("/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Every field event-details.js already reads stays exactly as it was -
    # this is purely additive, nothing here changes existing behavior.
    response = {
        "id": event.id,
        "title": event.title,
        "location": event.location,
        "description": event.description,
        "date_time": event.date_time,
        "price": event.price,
        "image_url": event.image_url,
        "total_seats": event.total_seats,
        "available_seats": event.available_seats,
        "category": event.category,
        "category_id": event.category_id,
        "inventory_type": event.inventory_type,
    }

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

    event.title = data.title
    event.location = data.location
    event.price = data.price
    event.image_url = data.image_url
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
    db: Session = Depends(get_db)
):
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