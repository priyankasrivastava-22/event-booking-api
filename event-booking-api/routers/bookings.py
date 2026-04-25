from fastapi import APIRouter, Depends, HTTPException
from core.limiter import limiter
from sqlalchemy.orm import Session
import models, schemas
from fastapi import Request
from utils.helpers import get_db
from core.security import get_current_user

router = APIRouter()


# ---------------- BOOK EVENT ----------------
@router.post("/book")
@limiter.limit("10/minute")
def book_event(
    request: Request,
    booking: schemas.BookingCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if booking.tickets <= 0:
        raise HTTPException(status_code=400, detail="Tickets must be greater than 0")

    # ATOMIC SEAT UPDATE (prevents race condition)
    updated = db.query(models.Event).filter(
        models.Event.id == booking.event_id,
        models.Event.available_seats >= booking.tickets
    ).update({
        models.Event.available_seats:
        models.Event.available_seats - booking.tickets
    })

    if updated == 0:
        raise HTTPException(status_code=400, detail="Not enough seats available")

    # CREATE BOOKING
    new_booking = models.Booking(
        user_name=user["username"],
        event_id=booking.event_id,
        tickets=booking.tickets
    )

    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    db.add(models.Notification(
        message=f"Booking confirmed for event {booking.event_id}",
        user_name=user["username"]
    ))
    db.commit()

    return new_booking


# ---------------- MY BOOKINGS ----------------
@router.get("/my-bookings")
def my_bookings(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    return db.query(models.Booking).filter(
        models.Booking.user_name == user["username"]
    ).all()


# ---------------- CANCEL BOOKING ----------------
@router.delete("/book/{booking_id}")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # OPTIONAL SECURITY
    if booking.user_name != user["username"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    # RETURN SEATS BACK
    db.query(models.Event).filter(
        models.Event.id == booking.event_id
    ).update({
        models.Event.available_seats:
        models.Event.available_seats + booking.tickets
    })

    db.delete(booking)

    db.add(models.Notification(
        message=f"Booking cancelled for event {booking.event_id}",
        user_name=user["username"]
    ))
    db.commit()

    return {"success": True, "message": "cancelled"}