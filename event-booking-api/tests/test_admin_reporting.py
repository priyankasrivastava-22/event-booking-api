"""Revenue must never count a held, unpaid reservation."""
import importlib
import sys
from datetime import datetime, timezone, timedelta

import models
from test_api_flow import environment


def test_paid_only_admin_statistics(environment):
    _, db = environment
    analytics = importlib.import_module("routers.analytics")
    customer = db.query(models.User).filter_by(username="alice").one()
    event = models.Event(title="Reporting concert", status="published", location="Hall",
                         date_time=(datetime.now(timezone.utc) + timedelta(days=5)).isoformat())
    db.add(event); db.flush()
    db.add_all([
        models.Booking(user_id=customer.id, event_id=event.id, tickets=2,
                       status=models.BOOKING_HELD, payment_status="pending", total_amount=9999),
        models.Booking(user_id=customer.id, event_id=event.id, tickets=1,
                       status=models.BOOKING_CONFIRMED, payment_status="paid", total_amount=599),
        models.Booking(user_id=customer.id, event_id=event.id, tickets=1,
                       status=models.BOOKING_CANCELLED, payment_status="cancelled", total_amount=2000),
    ])
    db.commit()
    user = {"username":"admin", "role":"admin"}
    assert analytics.dashboard(db=db, user=user)["total_tickets_sold"] == 1
    assert analytics.stats(db=db, user=user)["revenue"] == 599
    assert analytics.revenue(db=db, user=user)["total_revenue"] == 599
    current_year = datetime.now(timezone.utc).year
    yearly = analytics.overview(year=current_year, db=db, user=user)
    assert yearly["total_revenue"] == 599
    assert yearly["total_bookings"] == 1
    assert yearly["total_events"] == 1
    assert analytics.top_events(year=current_year, db=db, user=user)[0]["revenue"] == 599
    assert analytics.bookings_by_month(db=db,user=user)[0]["bookings"] == 1
    sys.modules.pop("routers.analytics", None)


def test_booking_dates_are_utc_for_browser_countdown(environment):
    _, db = environment
    from services.booking_presenter import serialize_booking
    user = db.query(models.User).filter_by(username="alice").one()
    event = models.Event(title="UTC browser test", location="Hall", status="draft")
    db.add(event); db.flush()
    booking = models.Booking(user_id=user.id, event_id=event.id, tickets=1,
                             status=models.BOOKING_HELD, payment_status="pending", total_amount=25,
                             booking_time=datetime.now(timezone.utc).replace(tzinfo=None),
                             expires_at=(datetime.now(timezone.utc) + timedelta(minutes=15)).replace(tzinfo=None))
    db.add(booking); db.commit()
    data = serialize_booking(booking)
    assert data["expires_at"].isoformat().endswith("+00:00")
    assert data["booking_time"].isoformat().endswith("+00:00")
