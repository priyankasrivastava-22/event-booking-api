"""Admin metrics derived from finalized orders, never provisional holds.

All monetary amounts represent recorded booking totals. With mock checkout
enabled they are simulated receipts, NOT real financial revenue.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

import models
from core.security import get_current_user
from routers.admin import admin_check
from utils.helpers import get_db

router = APIRouter()


def confirmed(db):
    return db.query(models.Booking).filter(
        models.Booking.status == models.BOOKING_CONFIRMED,
        models.Booking.payment_status == "paid",
    )


def total_amount(query):
    return query.with_entities(func.coalesce(func.sum(models.Booking.total_amount), 0)).scalar() or 0


def percent(current, previous):
    return round((current - previous) / previous * 100, 1) if previous else (100.0 if current else 0.0)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    return {
        "total_users": db.query(models.User).count(),
        "total_events": db.query(models.Event).count(),
        "total_bookings": confirmed(db).count(),
        "total_tickets_sold": confirmed(db).with_entities(func.coalesce(func.sum(models.Booking.tickets), 0)).scalar() or 0,
    }


@router.get("/most-booked")
def most_booked(db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    bookings = confirmed(db).with_entities(models.Booking.event_id, func.count(models.Booking.id).label("bookings"))\
        .group_by(models.Booking.event_id).all()
    counts = {event_id: count for event_id, count in bookings}
    return sorted(({"event_id": e.id, "title": e.title, "bookings": counts.get(e.id, 0)}
                   for e in db.query(models.Event).all()), key=lambda row: row["bookings"], reverse=True)


@router.get("/least-booked")
def least_booked(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return sorted(most_booked(db, user), key=lambda row: row["bookings"])


@router.get("/revenue")
def revenue(db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    return {"total_revenue": total_amount(confirmed(db))}


@router.get("/stats")
def stats(db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    return {"total_users": db.query(models.User).count(),
            "total_events": db.query(models.Event).count(),
            "total_bookings": confirmed(db).count(),
            "revenue": total_amount(confirmed(db))}


@router.get("/bookings-trend")
def bookings_trend(db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    since = datetime.now(timezone.utc) - timedelta(days=7)
    rows = confirmed(db).with_entities(func.date(models.Booking.booking_time).label("day"),
                      func.count(models.Booking.id).label("bookings"))\
        .filter(models.Booking.booking_time >= since)\
        .group_by(func.date(models.Booking.booking_time)).order_by(func.date(models.Booking.booking_time)).all()
    return [{"date": str(day), "bookings": count} for day, count in rows]


@router.get("/revenue-trend")
def revenue_trend(db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    since = datetime.now(timezone.utc) - timedelta(days=7)
    rows = confirmed(db).with_entities(func.date(models.Booking.booking_time).label("day"),
                      func.sum(models.Booking.total_amount).label("revenue"))\
        .filter(models.Booking.booking_time >= since)\
        .group_by(func.date(models.Booking.booking_time)).order_by(func.date(models.Booking.booking_time)).all()
    return [{"date": str(day), "revenue": amount} for day, amount in rows]


@router.get("/bookings-by-month")
def bookings_by_month(db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    year = datetime.now(timezone.utc).year
    rows = confirmed(db).with_entities(extract("month", models.Booking.booking_time).label("number"),
                      func.count(models.Booking.id).label("bookings"))\
        .filter(extract("year", models.Booking.booking_time) == year)\
        .group_by(extract("month", models.Booking.booking_time)).order_by(extract("month", models.Booking.booking_time)).all()
    return [{"month": datetime(year, int(month), 1).strftime("%b"), "bookings": count} for month, count in rows]


@router.get("/category-distribution")
def category_distribution(db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    rows = confirmed(db).join(models.Event, models.Event.id == models.Booking.event_id)\
        .with_entities(models.Event.category, func.count(models.Booking.id).label("bookings"))\
        .group_by(models.Event.category).all()
    total = sum(count for _, count in rows) or 1
    return sorted(({"category": category or "Uncategorized", "bookings": count,
                    "percentage": round(count / total * 100, 1)} for category, count in rows),
                  key=lambda row: row["bookings"], reverse=True)


@router.get("/overview")
def overview(year: int = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    year = year or datetime.now(timezone.utc).year
    current = confirmed(db).filter(extract("year", models.Booking.booking_time) == year)
    previous = confirmed(db).filter(extract("year", models.Booking.booking_time) == year - 1)
    current_revenue, previous_revenue = total_amount(current), total_amount(previous)
    current_bookings, previous_bookings = current.count(), previous.count()
    current_users = db.query(models.User).filter(models.User.created_at <= datetime(year, 12, 31, 23, 59, 59)).count()
    previous_users = db.query(models.User).filter(models.User.created_at <= datetime(year - 1, 12, 31, 23, 59, 59)).count()
    current_events = db.query(models.Event).filter(models.Event.date_time.like(f"{year}-%")).count()
    previous_events = db.query(models.Event).filter(models.Event.date_time.like(f"{year - 1}-%") - 1).count()
    return {"year": year, "total_revenue": current_revenue,
            "revenue_change_pct": percent(current_revenue, previous_revenue),
            "total_bookings": current_bookings, "bookings_change_pct": percent(current_bookings, previous_bookings),
            "total_users": current_users, "users_change_pct": percent(current_users, previous_users),
            "total_events": current_events, "events_change_pct": percent(current_events, previous_events)}


@router.get("/revenue-by-month")
def revenue_by_month(year: int = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    year = year or datetime.now(timezone.utc).year
    months = extract("month", models.Booking.booking_time)
    rows = confirmed(db).with_entities(months.label("number"),
                     func.sum(models.Booking.total_amount).label("revenue"))\
        .filter(extract("year", models.Booking.booking_time) == year)\
        .group_by(months).order_by(months).all()
    return [{"month": datetime(year, int(month), 1).strftime("%b"), "revenue": amount} for month, amount in rows]


@router.get("/top-events")
def top_events(year: int = None, limit: int = 5, db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    year = year or datetime.now(timezone.utc).year
    rows = confirmed(db).join(models.Event, models.Event.id == models.Booking.event_id)\
        .with_entities(models.Event.title, func.sum(models.Booking.total_amount).label("revenue"))\
        .filter(extract("year", models.Booking.booking_time) == year)\
        .group_by(models.Event.id, models.Event.title).order_by(func.sum(models.Booking.total_amount).desc())\
        .limit(max(1, min(limit, 100))).all()
    return [{"title": title, "revenue": amount} for title, amount in rows]
