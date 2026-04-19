from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas
from utils.helpers import get_db
from core.security import get_current_user

router = APIRouter()

@router.post("/book")
def book_event(booking: schemas.BookingCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    event = db.query(models.Event).filter(models.Event.id == booking.event_id).first()

    if event.available_seats < booking.tickets:
        raise HTTPException(status_code=400)

    event.available_seats -= booking.tickets

    new_booking = models.Booking(
        user_name=user["username"],
        event_id=booking.event_id,
        tickets=booking.tickets
    )

    db.add(new_booking)
    db.commit()
    return new_booking


@router.get("/my-bookings")
def my_bookings(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(models.Booking).filter(models.Booking.user_name == user["username"]).all()


@router.delete("/book/{booking_id}")
def cancel_booking(booking_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()

    event = db.query(models.Event).filter(models.Event.id == booking.event_id).first()
    event.available_seats += booking.tickets

    db.delete(booking)
    db.commit()

    return {"message": "cancelled"}