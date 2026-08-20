from fastapi import APIRouter, Depends, HTTPException, Request
from core.limiter import limiter
from sqlalchemy.orm import Session
import models
import schemas
from utils.helpers import get_db
from core.security import get_current_user

router = APIRouter()

@router.post("/book")                                                                                                    # BOOK EVENT
@limiter.limit("10/minute")
def book_event( request: Request, booking: schemas.BookingCreate, db: Session = Depends(get_db),user=Depends(get_current_user)):
    if booking.tickets <= 0: raise HTTPException( status_code=400, detail="Tickets must be greater than 0")
    db_user = db.query(models.User).filter( models.User.username == user["username"]).first()
    if not db_user: raise HTTPException( status_code=404, detail="User not found")
    event = db.query(models.Event).filter( models.Event.id == booking.event_id).first()
    if not event: raise HTTPException( status_code=404, detail="Event not found")
    updated = db.query(models.Event).filter(
        models.Event.id == booking.event_id,
        models.Event.available_seats >= booking.tickets
    ).update(
        {
            models.Event.available_seats:
                models.Event.available_seats - booking.tickets
        },
        synchronize_session=False
    )
    if updated == 0: raise HTTPException( status_code=400, detail="Not enough seats available")
    new_booking = models.Booking( user_id=db_user.id, event_id=booking.event_id, tickets=booking.tickets)
    db.add(new_booking)
    db.flush()
    notification = models.Notification(
        message=f"Booking confirmed for event {booking.event_id}",
        user_id=db_user.id
    )
    db.add(notification)
    # Commit EVERYTHING together. Seat deduction. Booking creation. Notification creation. Either all succeed or the transaction rolls back.
    db.commit()
    db.refresh(new_booking)
    return new_booking

@router.get("/my-bookings")                                                                                              # MY BOOKINGS
def my_bookings( user=Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter( models.User.username == user["username"]).first()                            # Resolve authenticated database user
    if not db_user: raise HTTPException( status_code=404, detail="User not found")
    bookings = db.query(models.Booking).filter( models.Booking.user_id == db_user.id).all()                              # Get bookings using user_id
    result = []
    for b in bookings:
        result.append(
            {
                "id": b.id, "tickets": b.tickets, "status": b.payment_status, "event": {
                    "title": b.event.title if b.event else "N/A",
                    "date_time": (
                        b.event.date_time
                        if b.event
                        else ""
                    ),
                    "location": (
                        b.event.location
                        if b.event
                        else ""
                    ),
                    "image_url": (
                        b.event.image_url
                        if b.event
                        else ""
                    ),
                    "category": (
                        b.event.category
                        if b.event
                        else ""
                    )
                }
            }
        )
    return result

@router.delete("/book/{booking_id}")                                                                                    # CANCEL BOOKING
def cancel_booking( booking_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    db_user = db.query(models.User).filter( models.User.username == user["username"]).first()
    if not db_user: raise HTTPException( status_code=404, detail="User not found")
    # Find booking belonging to this user. We check user_id directly in the query rather than fetching another user's booking and checking afterward.
    booking = db.query(models.Booking).filter( models.Booking.id == booking_id, models.Booking.user_id == db_user.id).first()
    if not booking: raise HTTPException( status_code=404, detail="Booking not found")
    updated = db.query(models.Event).filter(models.Event.id == booking.event_id).update(                                 # Restore seats
        {
            models.Event.available_seats: models.Event.available_seats + booking.tickets
        },
        synchronize_session=False
    )
    if updated == 0: raise HTTPException(status_code=404, detail="Event not found")
    event_id = booking.event_id
    db.delete(booking)
    notification = models.Notification( message=f"Booking cancelled for event {event_id}",user_id=db_user.id)
    db.add(notification)
    db.commit()
    return {
        "success": True,
        "message": "Booking cancelled successfully"
    }