from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas
from utils.helpers import get_db
from core.security import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])


# ---------------- ADMIN CHECK ----------------
def admin_check(user):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


# ---------------- USERS ----------------
@router.get("/users")
def users(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)
    return db.query(models.User).all()


# ---------------- ALL BOOKINGS ----------------
@router.get("/bookings")
def bookings(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)
    return db.query(models.Booking).all()


# ---------------- ADMIN CANCEL BOOKING ----------------
@router.delete("/bookings/{booking_id}")
def admin_cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    admin_check(user)

    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    #  RETURN SEATS BACK
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

    return {"success": True, "message": "Booking cancelled by admin"}