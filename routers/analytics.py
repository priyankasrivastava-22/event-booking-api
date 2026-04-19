from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
from core.security import get_db, get_current_user

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