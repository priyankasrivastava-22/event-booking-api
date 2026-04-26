from fastapi import APIRouter, Depends, HTTPException, Request
from core.limiter import limiter
from sqlalchemy.orm import Session
import models, schemas
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

    updated = db.query(models.Event).filter(
        models.Event.id == booking.event_id,
        models.Event.available_seats >= booking.tickets
    ).update({
        models.Event.available_seats:
        models.Event.available_seats - booking.tickets
    })

    if updated == 0:
        raise HTTPException(status_code=400, detail="Not enough seats available")

    new_booking = models.Booking(
        user_name=user["username"],
        event_id=booking.event_id,
        tickets=booking.tickets
    )

    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    # notification
    db.add(models.Notification(
        message=f"Booking confirmed for event {booking.event_id}",
        user_name=user["username"]
    ))
    db.commit()

    return new_booking


# ---------------- MY BOOKINGS ----------------
@router.get("/my-bookings")
def my_bookings(user=Depends(get_current_user), db: Session = Depends(get_db)):

    bookings = db.query(models.Booking).filter(
        models.Booking.user_name == user["username"]
    ).all()

    result = []

    for b in bookings:
        result.append({
            "id": b.id,
            "tickets": b.tickets,
            "status": getattr(b, "status", "confirmed"),
            "event": {
                "title": b.event.title if b.event else "N/A",
                "date_time": b.event.date_time if b.event else "",
                "location": b.event.location if b.event else ""
            }
        })

    return result


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

    if booking.user_name != user["username"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    # restore seats
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