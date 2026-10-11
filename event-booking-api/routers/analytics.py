from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
from core.security import get_current_user
from datetime import datetime, timedelta
from sqlalchemy import func
from routers.admin import admin_check
from utils.helpers import get_db

router = APIRouter()

@router.get("/dashboard")                                                                                                # DASHBOARD
def admin_dashboard(db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")
    return {
        "total_users": db.query(models.User).count(),
        "total_events": db.query(models.Event).count(),
        "total_bookings": db.query(models.Booking).count(),
        "total_tickets_sold": sum(b.tickets for b in db.query(models.Booking).all())
    }

@router.get("/most-booked")                                                                                              # MOST BOOKED
def most_booked(db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")
    events = db.query(models.Event).all()
    result = []
    for e in events:
        count = db.query(models.Booking).filter(models.Booking.event_id == e.id).count()
        result.append({"event_id": e.id, "title": e.title, "bookings": count})
    return sorted(result, key=lambda x: x["bookings"], reverse=True)

@router.get("/least-booked")                                                                                             # LEAST BOOKED
def least_booked(db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")
    events = db.query(models.Event).all()
    result = []
    for e in events:
        count = db.query(models.Booking).filter(models.Booking.event_id == e.id).count()
        result.append({"event_id": e.id, "title": e.title, "bookings": count})
    return sorted(result, key=lambda x: x["bookings"])

@router.get("/revenue")                                                                                                  # REVENUE
def revenue(db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")
    total = 0
    for b in db.query(models.Booking).all():
        event = db.query(models.Event).filter(models.Event.id == b.event_id).first()
        if event:
            total += b.tickets * event.price
    return {"total_revenue": total}

@router.get("/stats")                                                                                                    # STATS (SUMMARY DASHBOARD) ---------------
def get_admin_stats(db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    total_users = db.query(models.User).count()
    total_events = db.query(models.Event).count()
    total_bookings = db.query(models.Booking).count()
    revenue = 0
    bookings = db.query(models.Booking).all()
    for b in bookings:
        event = db.query(models.Event).filter(models.Event.id == b.event_id).first()
        if event:
            revenue += event.price * b.tickets
    return {
        "total_users": total_users,
        "total_events": total_events,
        "total_bookings": total_bookings,
        "revenue": revenue
    }

@router.get("/bookings-trend")                                                                                           # BOOKINGS TREND
def bookings_trend(db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    today = datetime.utcnow()
    last_7_days = today - timedelta(days=7)
    results = (
        db.query(func.date(models.Booking.booking_time).label("date"), func.count(models.Booking.id).label("bookings"))
        .filter(models.Booking.booking_time >= last_7_days)
        .group_by(func.date(models.Booking.booking_time))
        .all()
    )
    return [
        {"date": r.date, "bookings": r.bookings}
        for r in results
    ]

@router.get("/revenue-trend")                                                                                            # REVENUE TREND
def revenue_trend(db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    today = datetime.utcnow()
    last_7_days = today - timedelta(days=7)
    bookings = db.query(models.Booking).filter(models.Booking.booking_time >= last_7_days).all()
    trend = {}
    for b in bookings:
        date = b.booking_time.date()
        event = db.query(models.Event).filter(models.Event.id == b.event_id).first()
        if event:
            trend[str(date)] = trend.get(str(date), 0) + (event.price * b.tickets)
    return [
        {"date": k, "revenue": v}
        for k, v in trend.items()
    ]

@router.get("/bookings-by-month")                                                                                        # BOOKINGS PER MONTH
def bookings_by_month(db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    since = datetime.utcnow() - timedelta(days=365)
    results = (
        db.query(
            func.to_char(models.Booking.booking_time, 'Mon').label("month"),
            func.extract('month', models.Booking.booking_time).label("month_number"),
            func.count(models.Booking.id).label("bookings"),
        )
        .filter(models.Booking.booking_time >= since)
        .group_by("month", "month_number")
        .order_by("month_number")
        .all()
    )
    return [{"month": r.month, "bookings": r.bookings} for r in results]

@router.get("/category-distribution")                                                                                    # CATEGORY DISTRIBUTION
def category_distribution(db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    results = (
        db.query(models.Event.category, func.count(models.Booking.id).label("bookings"))
        .join(models.Booking, models.Booking.event_id == models.Event.id)
        .group_by(models.Event.category)
        .all()
    )
    total = sum(r.bookings for r in results) or 1
    data = [
        {
            "category": r.category or "Uncategorized",
            "bookings": r.bookings,
            "percentage": round((r.bookings / total) * 100, 1)
        }
        for r in results
    ]
    return sorted(data, key=lambda x: x["bookings"], reverse=True)

@router.get("/overview")                                                                                                 # ANALYTICS OVERVIEW — 4 stat cards with year-over-year % change
def analytics_overview(year: int = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    year = year or datetime.utcnow().year
    previous_year = year - 1

    def bookings_query(y):
        return db.query(models.Booking).filter(func.extract('year', models.Booking.booking_time) == y)

    revenue_this_year = bookings_query(year).with_entities(func.coalesce(func.sum(models.Booking.total_amount), 0)).scalar()
    revenue_last_year = bookings_query(previous_year).with_entities(func.coalesce(func.sum(models.Booking.total_amount), 0)).scalar()

    bookings_this_year = bookings_query(year).count()
    bookings_last_year = bookings_query(previous_year).count()

    year_end = datetime(year, 12, 31, 23, 59, 59)
    previous_year_end = datetime(previous_year, 12, 31, 23, 59, 59)

    users_this_year = db.query(models.User).filter(models.User.created_at <= year_end).count()
    users_last_year = db.query(models.User).filter(models.User.created_at <= previous_year_end).count()

    events_this_year = db.query(models.Event).filter(models.Event.date_time.like(f"{year}-%")).count()
    events_last_year = db.query(models.Event).filter(models.Event.date_time.like(f"{previous_year}-%")).count()

    def pct_change(current, previous):
        if not previous:
            return 100.0 if current else 0.0
        return round(((current - previous) / previous) * 100, 1)

    return {
        "year": year,
        "total_revenue": revenue_this_year,
        "revenue_change_pct": pct_change(revenue_this_year, revenue_last_year),
        "total_bookings": bookings_this_year,
        "bookings_change_pct": pct_change(bookings_this_year, bookings_last_year),
        "total_users": users_this_year,
        "users_change_pct": pct_change(users_this_year, users_last_year),
        "total_events": events_this_year,
        "events_change_pct": pct_change(events_this_year, events_last_year),
    }


@router.get("/revenue-by-month")                                                                                         # REVENUE OVER TIME — full year, monthly, for the selected year
def revenue_by_month(year: int = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    year = year or datetime.utcnow().year
    results = (
        db.query(
            func.to_char(models.Booking.booking_time, 'Mon').label("month"),
            func.extract('month', models.Booking.booking_time).label("month_number"),
            func.coalesce(func.sum(models.Booking.total_amount), 0).label("revenue"),
        )
        .filter(func.extract('year', models.Booking.booking_time) == year)
        .group_by("month", "month_number")
        .order_by("month_number")
        .all()
    )
    return [{"month": r.month, "revenue": r.revenue} for r in results]


@router.get("/top-events")                                                                                               # TOP PERFORMING EVENTS — by revenue, for the selected year
def top_events(year: int = None, limit: int = 5, db: Session = Depends(get_db), user=Depends(get_current_user)):
    admin_check(user)
    year = year or datetime.utcnow().year
    results = (
        db.query(models.Event.title, func.coalesce(func.sum(models.Booking.total_amount), 0).label("revenue"))
        .join(models.Booking, models.Booking.event_id == models.Event.id)
        .filter(func.extract('year', models.Booking.booking_time) == year)
        .group_by(models.Event.id, models.Event.title)
        .order_by(func.sum(models.Booking.total_amount).desc())
        .limit(limit)
        .all()
    )
    return [{"title": r.title, "revenue": r.revenue} for r in results]