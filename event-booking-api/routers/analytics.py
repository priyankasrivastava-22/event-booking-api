from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
from core.security import get_db, get_current_user
from datetime import datetime, timedelta
from sqlalchemy import func
from routers.admin import admin_check

router = APIRouter()

# ---------------- DASHBOARD ----------------
@router.get("/admin/dashboard")
def admin_dashboard(db: Session = Depends(get_db), user=Depends(get_current_user)):

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    return {
        "total_users": db.query(models.User).count(),
        "total_events": db.query(models.Event).count(),
        "total_bookings": db.query(models.Booking).count(),
        "total_tickets_sold": sum(b.tickets for b in db.query(models.Booking).all())
    }


# ---------------- MOST BOOKED ----------------
@router.get("/admin/analytics/most-booked")
def most_booked(db: Session = Depends(get_db), user=Depends(get_current_user)):

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    events = db.query(models.Event).all()

    result = []
    for e in events:
        count = db.query(models.Booking).filter(models.Booking.event_id == e.id).count()
        result.append({"event_id": e.id, "title": e.title, "bookings": count})

    return sorted(result, key=lambda x: x["bookings"], reverse=True)


# ---------------- LEAST BOOKED ----------------
@router.get("/admin/analytics/least-booked")
def least_booked(db: Session = Depends(get_db), user=Depends(get_current_user)):

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    events = db.query(models.Event).all()

    result = []
    for e in events:
        count = db.query(models.Booking).filter(models.Booking.event_id == e.id).count()
        result.append({"event_id": e.id, "title": e.title, "bookings": count})

    return sorted(result, key=lambda x: x["bookings"])


# ---------------- REVENUE ----------------
@router.get("/admin/analytics/revenue")
def revenue(db: Session = Depends(get_db), user=Depends(get_current_user)):

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    total = 0
    for b in db.query(models.Booking).all():
        event = db.query(models.Event).filter(models.Event.id == b.event_id).first()
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