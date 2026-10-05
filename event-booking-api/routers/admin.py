from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import models, schemas
from utils.helpers import get_db
from core.security import get_current_user
from sqlalchemy import func, String
from datetime import datetime

router = APIRouter()

# ---------------- ADMIN CHECK ----------------
def admin_check(user):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


def get_db_user(user, db: Session):                                                                  # RESOLVE AUTHENTICATED DATABASE USER (matches bookings.py/payment.py pattern)
    db_user = db.query(models.User).filter(models.User.username == user["username"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Admin user not found")
    return db_user


# ---------------- USERS ----------------
@router.get("/users")
def users(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)
    return db.query(models.User).all()


# ---------------- ALL BOOKINGS ----------------
@router.get("/bookings/list")                                                                                            # ADMIN BOOKINGS LIST — with stats, joins, filters, pagination
def get_bookings_admin(
    page: int = 1,
    limit: int = 10,
    search: str = None,
    event_id: int = None,
    status: str = None,
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)

    base_query = db.query(models.Booking)

    if search:
        base_query = base_query.join(models.User, models.User.id == models.Booking.user_id).filter(
            (models.User.username.ilike(f"%{search}%")) |
            (models.User.full_name.ilike(f"%{search}%")) |
            (models.Booking.id.cast(String).ilike(f"%{search}%"))
        )
    if event_id:
        base_query = base_query.filter(models.Booking.event_id == event_id)
    if status:
        base_query = base_query.filter(models.Booking.status == status)
    if start_date:
        base_query = base_query.filter(models.Booking.booking_time >= start_date)
    if end_date:
        base_query = base_query.filter(models.Booking.booking_time <= end_date)

    total = base_query.count()
    skip = (page - 1) * limit
    bookings = base_query.order_by(models.Booking.id.desc()).offset(skip).limit(limit).all()

    today = datetime.utcnow().date()
    stats = {
        "today": db.query(func.count(models.Booking.id)).filter(func.date(models.Booking.booking_time) == today).scalar(),
        "pending": db.query(func.count(models.Booking.id)).filter(models.Booking.status == "pending").scalar(),
        "completed": db.query(func.count(models.Booking.id)).filter(models.Booking.status == "confirmed").scalar(),
        "cancelled": db.query(func.count(models.Booking.id)).filter(models.Booking.status == "cancelled").scalar(),
    }

    items = []
    for b in bookings:
        booking_user = db.query(models.User).filter(models.User.id == b.user_id).first()
        booking_event = db.query(models.Event).filter(models.Event.id == b.event_id).first()
        items.append({
            "id": b.id,
            "user_name": booking_user.full_name or booking_user.username if booking_user else "—",
            "event_title": booking_event.title if booking_event else "—",
            "tickets": b.tickets,
            "total_amount": b.total_amount,
            "status": b.status,
            "booking_time": b.booking_time,
        })

    return {
        "items": items,
        "stats": stats,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": max(1, (total + limit - 1) // limit)
    }

# ---------------- ADMIN CANCEL BOOKING ----------------
@router.delete("/bookings/{booking_id}")
def admin_cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)

    try:
        booking = db.query(models.Booking).filter(
            models.Booking.id == booking_id
        ).with_for_update().first()

        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        if booking.status == models.BOOKING_CANCELLED:
            raise HTTPException(status_code=400, detail="Booking is already cancelled")

        # RELEASE HELD/SOLD INVENTORY BACK TO AVAILABLE (seat/zone/ticket_type architecture)
        for item in booking.items:
            inventory = item.inventory
            if inventory:
                inventory.status = models.INVENTORY_AVAILABLE
                inventory.lock_token = None
                inventory.locked_until = None
                if inventory.seat_id:
                    seat = db.query(models.Seat).filter(models.Seat.id == inventory.seat_id).first()
                    if seat:
                        seat.status = models.SEAT_AVAILABLE
            item.status = models.BOOKING_CANCELLED

        # CANCEL ANY ISSUED TICKETS TIED TO THIS BOOKING
        for ticket in booking.tickets_rel:
            if ticket.status != models.TICKET_CANCELLED:
                ticket.status = models.TICKET_CANCELLED

        # LEGACY GENERAL-ADMISSION BOOKINGS: RETURN SEATS TO THE EVENT COUNTER
        if booking.tickets and not booking.items:
            db.query(models.Event).filter(
                models.Event.id == booking.event_id
            ).update({
                models.Event.available_seats: models.Event.available_seats + booking.tickets
            })

        booking.status = models.BOOKING_CANCELLED
        booking.payment_status = "cancelled"

        db_admin = get_db_user(user, db)
        db.add(models.Notification(
            user_id=db_admin.id,
            message=f"Booking #{booking.id} cancelled by admin for event {booking.event_id}"
        ))

        db.commit()

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to cancel booking") from exc

    return {"success": True, "message": "Booking cancelled by admin"}


#-----------------DEACTIVATE USER----------------------
@router.delete("/users/{user_id}")
def delete_user(user_id: int,
                db: Session = Depends(get_db),
                user=Depends(get_current_user)):

    admin_check(user)

    db_user = db.query(models.User).filter(
        models.User.id == user_id
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if db_user.username == user["username"]:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    # SOFT-DEACTIVATE RATHER THAN HARD DELETE: preserves payment/ticket/audit history
    # and matches the login check (get_authenticated_user rejects inactive accounts).
    db_user.is_active = False
    db.commit()

    return {"message": "User deactivated"}

#------------------DELETE EVENT---------------------
@router.delete("/events/{event_id}")
def delete_event(event_id: int,
                 db: Session = Depends(get_db),
                 user=Depends(get_current_user)):

    admin_check(user)

    event = db.query(models.Event).filter(
        models.Event.id == event_id
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # PREVENT DELETING AN EVENT THAT STILL HAS LIVE BOOKINGS
    # (event_id FK cascades ON DELETE, which would silently wipe those bookings/payments)
    active_bookings = db.query(models.Booking).filter(
        models.Booking.event_id == event_id,
        models.Booking.status.notin_([
            models.BOOKING_CANCELLED,
            models.BOOKING_EXPIRED,
            models.BOOKING_FAILED,
        ])
    ).count()

    if active_bookings > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete event with {active_bookings} active booking(s). Cancel them first."
        )

    db.delete(event)
    db.commit()

    return {"message": "Event deleted"}

#---------------------UPDATE EVENT--------------
@router.put("/events/{id}")
def update_event(id: int, data: schemas.EventUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):

    admin_check(user)

    event = db.query(models.Event).filter(models.Event.id == id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(event, key, value)

    db.commit()
    db.refresh(event)

    return event


@router.post("/events/{event_id}/layout", response_model=schemas.LayoutResponse)
def create_layout(
    event_id: int,
    layout_data: schemas.LayoutCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)

    event = db.query(models.Event).filter(
        models.Event.id == event_id
    ).first()

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Event not found"
        )

    existing = db.query(models.VenueLayout).filter(
        models.VenueLayout.event_id == event_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Venue layout already exists"
        )

    # THE PATH event_id IS THE AUTHORITY, NOT THE REQUEST BODY
    layout = models.VenueLayout(
        event_id=event_id,
        name=layout_data.name,
        version=layout_data.version,
        is_active=layout_data.is_active,
    )

    try:
        db.add(layout)
        db.commit()
        db.refresh(layout)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Layout version already exists for this event") from exc

    return layout


@router.post("/layouts/{layout_id}/zones", response_model=schemas.ZoneResponse)
def create_zone(
    layout_id: int,
    zone_data: schemas.ZoneCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)

    layout = db.query(models.VenueLayout).filter(
        models.VenueLayout.id == layout_id
    ).first()

    if not layout:
        raise HTTPException(
            status_code=404,
            detail="Layout not found"
        )

    # DERIVE event_id FROM THE LAYOUT ITSELF, NEVER FROM CLIENT INPUT
    zone = models.EventZone(
        event_id=layout.event_id,
        layout_id=layout.id,
        name=zone_data.name,
        code=zone_data.code,
        zone_type=zone_data.zone_type,
        capacity=zone_data.capacity,
        base_price=zone_data.base_price,
        is_active=zone_data.is_active,
    )

    try:
        db.add(zone)
        db.commit()
        db.refresh(zone)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A zone with this code already exists for this event") from exc

    return zone

@router.get("/users/list")                                                                                               # ADMIN USERS LIST — paginated, with booking counts
def get_users_admin(
    page: int = 1,
    limit: int = 10,
    search: str = None,
    role: str = None,
    status: str = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)

    query = db.query(models.User)

    if search:
        query = query.filter(
            (models.User.username.ilike(f"%{search}%")) |
            (models.User.email.ilike(f"%{search}%")) |
            (models.User.full_name.ilike(f"%{search}%"))
        )
    if role:
        query = query.filter(models.User.role == role)
    if status == "active":
        query = query.filter(models.User.is_active == True)
    elif status == "inactive":
        query = query.filter(models.User.is_active == False)

    total = query.count()
    skip = (page - 1) * limit
    users = query.order_by(models.User.id.desc()).offset(skip).limit(limit).all()

    booking_counts = dict(
        db.query(models.Booking.user_id, func.count(models.Booking.id))
        .filter(models.Booking.user_id.in_([u.id for u in users]) if users else False)
        .group_by(models.Booking.user_id)
        .all()
    )

    items = [
        {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "profile_image": u.profile_image,
            "bookings_count": booking_counts.get(u.id, 0),
        }
        for u in users
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": max(1, (total + limit - 1) // limit)
    }


@router.put("/users/{user_id}")                                                                                          # ADMIN UPDATE USER — role/status
def update_user_admin(
    user_id: int,
    data: schemas.UserAdminUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)

    target = db.query(models.User).filter(models.User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if data.role is not None:
        target.role = data.role
    if data.is_active is not None:
        target.is_active = data.is_active

    db.commit()
    db.refresh(target)
    return {"id": target.id, "role": target.role, "is_active": target.is_active}

@router.post("/announcements", response_model=schemas.AnnouncementResponse)                                              # SEND ANNOUNCEMENT — records it + creates a personal notification for each matching user
def create_announcement(data: schemas.AnnouncementCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)

    query = db.query(models.User)
    if data.audience == "registered":
        query = query.filter(models.User.email_verified == True)
    recipients = query.all()

    announcement = models.Announcement(title=data.title, message=data.message, audience=data.audience, sent_count=len(recipients))
    db.add(announcement)

    for recipient in recipients:
        db.add(models.Notification(message=f"{data.title}: {data.message}", user_id=recipient.id))

    db.commit()
    db.refresh(announcement)
    return announcement


@router.get("/announcements")                                                                                            # ANNOUNCEMENT HISTORY — paginated
def get_announcements(page: int = 1, limit: int = 5, db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    query = db.query(models.Announcement).order_by(models.Announcement.id.desc())
    total = query.count()
    skip = (page - 1) * limit
    items = query.offset(skip).limit(limit).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": max(1, (total + limit - 1) // limit)
    }