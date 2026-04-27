from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas
from utils.helpers import get_db
from core.security import get_current_user
from datetime import datetime, timedelta
from sqlalchemy import func

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

#-----------------DELETE USER----------------------
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

    db.delete(db_user)
    db.commit()

    return {"message": "User deleted"}

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

    db.delete(event)
    db.commit()

    return {"message": "Event deleted"}

#---------------------UPDATE EVENT--------------
@router.put("/events/{event_id}")
def update_event(event_id: int,
                 updated: schemas.EventCreate,
                 db: Session = Depends(get_db),
                 user=Depends(get_current_user)):

    admin_check(user)

    event = db.query(models.Event).filter(
        models.Event.id == event_id
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    for key, value in updated.dict().items():
        setattr(event, key, value)

    db.commit()

    return {"message": "Event updated"}


@router.put("/events/{id}")
def update_event(id: int, data: schemas.EventUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):

    admin_check(user)

    event = db.query(models.Event).filter(models.Event.id == id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    for key, value in data.dict(exclude_unset=True).items():
        setattr(event, key, value)

    db.commit()
    db.refresh(event)

    return event

# ---------------- DASHBOARD ----------------
@router.get("/admin/dashboard")
def admin_dashboard(db: Session = Depends(get_db), user=Depends(get_current_user)):

    admin_check(user)

    return {
        "total_users": db.query(models.User).count(),
        "total_events": db.query(models.Event).count(),
        "total_bookings": db.query(models.Booking).count(),
        "total_tickets_sold": sum(b.tickets for b in db.query(models.Booking).all())
    }


# ---------------- MOST BOOKED ----------------
@router.get("/admin/analytics/most-booked")
def most_booked(db: Session = Depends(get_db), user=Depends(get_current_user)):

    admin_check(user)

    events = db.query(models.Event).all()

    result = []
    for e in events:
        count = db.query(models.Booking).filter(
            models.Booking.event_id == e.id
        ).count()

        result.append({
            "event_id": e.id,
            "title": e.title,
            "bookings": count
        })

    return sorted(result, key=lambda x: x["bookings"], reverse=True)


# ---------------- LEAST BOOKED ----------------
@router.get("/admin/analytics/least-booked")
def least_booked(db: Session = Depends(get_db), user=Depends(get_current_user)):

    admin_check(user)

    events = db.query(models.Event).all()

    result = []
    for e in events:
        count = db.query(models.Booking).filter(
            models.Booking.event_id == e.id
        ).count()

        result.append({
            "event_id": e.id,
            "title": e.title,
            "bookings": count
        })

    return sorted(result, key=lambda x: x["bookings"])


# ---------------- REVENUE (TOTAL) ----------------
@router.get("/admin/analytics/revenue")
def revenue(db: Session = Depends(get_db), user=Depends(get_current_user)):

    admin_check(user)

    total = 0

    for b in db.query(models.Booking).all():
        event = db.query(models.Event).filter(
            models.Event.id == b.event_id
        ).first()

        if event:
            total += b.tickets * event.price

    return {"total_revenue": total}


# ---------------- STATS (SUMMARY DASHBOARD) ----------------
@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    admin_check(user)

    total_users = db.query(models.User).count()
    total_events = db.query(models.Event).count()
    total_bookings = db.query(models.Booking).count()

    revenue = 0

    bookings = db.query(models.Booking).all()
    for b in bookings:
        event = db.query(models.Event).filter(
            models.Event.id == b.event_id
        ).first()

        if event:
            revenue += event.price * b.tickets

    return {
        "total_users": total_users,
        "total_events": total_events,
        "total_bookings": total_bookings,
        "revenue": revenue
    }


# ---------------- BOOKINGS TREND ----------------
@router.get("/admin/analytics/bookings-trend")
def bookings_trend(db: Session = Depends(get_db), user=Depends(get_current_user)):

    admin_check(user)

    today = datetime.utcnow()
    last_7_days = today - timedelta(days=7)

    results = (
        db.query(
            func.date(models.Booking.booking_time).label("date"),
            func.count(models.Booking.id).label("bookings")
        )
        .filter(models.Booking.booking_time >= last_7_days)
        .group_by(func.date(models.Booking.booking_time))
        .all()
    )

    return [
        {"date": r.date, "bookings": r.bookings}
        for r in results
    ]


# ---------------- REVENUE TREND ----------------
@router.get("/admin/analytics/revenue-trend")
def revenue_trend(db: Session = Depends(get_db), user=Depends(get_current_user)):

    admin_check(user)

    today = datetime.utcnow()
    last_7_days = today - timedelta(days=7)

    bookings = db.query(models.Booking).filter(
        models.Booking.booking_time >= last_7_days
    ).all()

    trend = {}

    for b in bookings:
        date = b.booking_time.date()

        event = db.query(models.Event).filter(
            models.Event.id == b.event_id
        ).first()

        if event:
            trend[str(date)] = trend.get(str(date), 0) + (
                event.price * b.tickets
            )

    return [
        {"date": k, "revenue": v}
        for k, v in trend.items()
    ]