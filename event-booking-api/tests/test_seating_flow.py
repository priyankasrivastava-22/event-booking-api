"""Offline regression tests for Eventora's three inventory models.

Run: pytest -q tests/test_seating_flow.py
This fixture uses in-memory SQLite. PostgreSQL concurrent-worker behavior needs a
separate integration test against a real disposable PostgreSQL database.
"""
import importlib
import sys
import types
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from schemas_seating import LayoutCreate, ZoneCreate, RowCreate
from services.booking_service import BookingService
from services.inventory_service import InventoryService


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    models.Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def seats_api(monkeypatch):
    # No real JWT needed for direct admin-function tests; use injected admin identity.
    auth = types.ModuleType("core.security")
    auth.get_current_user = lambda: None
    with monkeypatch.context() as p:
        p.setitem(sys.modules, "core.security", auth)
        sys.modules.pop("routers.seating", None)
        seating = importlib.import_module("routers.seating")
        yield seating
        sys.modules.pop("routers.seating", None)


def seed(db, kind):
    u1 = models.User(username=f"u1_{kind}", password="unused", is_active=True)
    u2 = models.User(username=f"u2_{kind}", password="unused", is_active=True)
    event = models.Event(title=f"{kind} event", location="Venue", inventory_type=kind)
    db.add_all([u1, u2, event])
    db.commit()
    return u1, u2, event


def test_seat_admin_setup_atomic_hold_and_sale(db, seats_api):
    user, other, event = seed(db, "seat")
    admin = {"role": "admin"}
    layout = seats_api.create_layout(event.id, LayoutCreate(event_id=event.id, name="Auditorium"), db, admin)
    assert seats_api.get_layout(event.id, db, admin).id == layout.id
    vip = seats_api.create_zone(layout.id, ZoneCreate(name="VIP", code="VIP", zone_type="seated", capacity=5, base_price=700), db, admin)
    assert seats_api.list_zones(layout.id, db, admin)[0]["code"] == "VIP"
    result = seats_api.create_row(vip["id"], RowCreate(zone_id=vip["id"], row_label="A", seat_count=3), db, admin)
    assert result["seats_created"] == 3
    assert len(seats_api.list_rows(vip["id"], db, admin)) == 1
    assert db.query(models.Inventory).filter_by(event_id=event.id).count() == 3
    with pytest.raises(HTTPException) as exc:
        seats_api.create_row(vip["id"], RowCreate(zone_id=vip["id"], row_label="B", seat_count=3), db, admin)
    assert exc.value.status_code == 400

    seat_id = seats_api.get_event_seats(event.id, db)[0]["id"]
    own = BookingService(db).create_hold(user.id, event.id, "first-seat")
    booking = InventoryService(db).hold_seats(event.id, [seat_id], user.id, own.id)
    assert booking.total_amount == 700 and booking.tickets == 1
    assert seats_api.get_event_seats(event.id, db)[0]["status"] == "locked"
    other_booking = BookingService(db).create_hold(other.id, event.id, "second-seat")
    with pytest.raises(ValueError, match="no longer available"):
        InventoryService(db).hold_seats(event.id, [seat_id], other.id, other_booking.id)
    db.rollback()
    # Checkout confirms all inventory + Ticket rows in the same transaction.
    finalized = BookingService(db).confirm_booking(booking.id, user.id)
    assert finalized.status == "confirmed" and finalized.tickets == 1
    assert db.query(models.Ticket).filter_by(booking_id=booking.id, seat_id=seat_id).count() == 1
    assert seats_api.get_event_seats(event.id, db)[0]["status"] == "sold"
    with pytest.raises(ValueError, match="no longer available"):
        InventoryService(db).hold_seats(event.id, [seat_id], other.id, other_booking.id)
    db.rollback()
    with pytest.raises(HTTPException) as exc:
        seats_api.delete_zone(vip["id"], db, admin)
    assert exc.value.status_code == 409


def test_pooled_zone_holds_cannot_exceed_capacity(db, seats_api):
    user, other, event = seed(db, "zone")
    admin = {"role": "admin"}
    layout = seats_api.create_layout(event.id, LayoutCreate(event_id=event.id, name="Festival"), db, admin)
    z = seats_api.create_zone(layout.id, ZoneCreate(name="Standing VIP", code="SVIP", zone_type="general", capacity=3, base_price=350), db, admin)
    b1 = BookingService(db).create_hold(user.id, event.id)
    b1 = InventoryService(db).hold_zone(event.id, z["id"], 2, user.id, b1.id)
    b2 = BookingService(db).create_hold(other.id, event.id)
    with pytest.raises(ValueError, match="Only 1"):
        InventoryService(db).hold_zone(event.id, z["id"], 2, other.id, b2.id)
    db.rollback()
    assert b1.total_amount == 700 and b1.tickets == 2
    assert BookingService(db).confirm_booking(b1.id, user.id).status == "confirmed"
    assert db.query(models.Ticket).filter_by(booking_id=b1.id, zone_id=z["id"]).count() == 2
    assert db.get(models.EventZone, z["id"]).sold_count == 2
    InventoryService(db).hold_zone(event.id, z["id"], 1, other.id, b2.id)
    assert db.get(models.EventZone, z["id"]).locked_count == 1


def test_general_pass_stock_price_and_retries(db):
    user, other, event = seed(db, "general")
    pass_type = models.TicketType(event_id=event.id, name="Early Bird", price=199, inventory_limit=4)
    db.add(pass_type)
    db.commit()
    first = BookingService(db).create_hold(user.id, event.id, "general-key")
    assert BookingService(db).create_hold(user.id, event.id, "general-key").id == first.id
    with pytest.raises(ValueError, match="another user or event"):
        BookingService(db).create_hold(other.id, event.id, "general-key")
    db.rollback()
    held = InventoryService(db).hold_passes(event.id, pass_type.id, 3, user.id, first.id)
    assert held.total_amount == 597 and held.tickets == 3
    second = BookingService(db).create_hold(other.id, event.id)
    with pytest.raises(ValueError, match="Only 1"):
        InventoryService(db).hold_passes(event.id, pass_type.id, 2, other.id, second.id)
    db.rollback()
    BookingService(db).confirm_booking(first.id, user.id)
    assert db.query(models.Ticket).filter_by(booking_id=first.id, ticket_type_id=pass_type.id).count() == 3
    assert db.get(models.TicketType, pass_type.id).sold_count == 3


def test_expired_seat_hold_is_reclaimed(db, seats_api):
    user, other, event = seed(db, "seat")
    admin = {"role": "admin"}
    layout = seats_api.create_layout(event.id, LayoutCreate(event_id=event.id, name="Hall"), db, admin)
    zone = seats_api.create_zone(layout.id, ZoneCreate(name="Main", code="M", zone_type="seated", capacity=1, base_price=200), db, admin)
    seats_api.create_row(zone["id"], RowCreate(zone_id=zone["id"], row_label="A", seat_count=1), db, admin)
    seat_id = seats_api.get_event_seats(event.id, db)[0]["id"]
    booking = BookingService(db).create_hold(user.id, event.id)
    InventoryService(db).hold_seats(event.id, [seat_id], user.id, booking.id)
    db.get(models.Booking, booking.id).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    with pytest.raises(ValueError, match="expired"):
        BookingService(db).confirm_booking(booking.id, user.id)
    db.rollback()
    assert InventoryService(db).release_expired_holds() == 1
    second = BookingService(db).create_hold(other.id, event.id)
    InventoryService(db).hold_seats(event.id, [seat_id], other.id, second.id)
    assert db.get(models.Booking, second.id).status == "held"


def test_mock_checkout_issues_tickets_and_rejects_double_payment(db, seats_api, monkeypatch):
    monkeypatch.setenv("ENABLE_MOCK_PAYMENTS", "true")
    import schemas
    import importlib
    import sys
    user, _, event = seed(db, "seat")
    admin = {"role": "admin"}
    layout = seats_api.create_layout(event.id, LayoutCreate(event_id=event.id, name="Stage"), db, admin)
    zone = seats_api.create_zone(layout.id, ZoneCreate(name="VIP", code="VIP", zone_type="seated", capacity=2, base_price=499), db, admin)
    seats_api.create_row(zone["id"], RowCreate(zone_id=zone["id"], row_label="A", seat_count=2), db, admin)
    seat_id = seats_api.get_event_seats(event.id, db)[0]["id"]
    pending = BookingService(db).create_hold(user.id, event.id)
    InventoryService(db).hold_seats(event.id, [seat_id], user.id, pending.id)
    sys.modules.pop("routers.payment", None)
    payment_api = importlib.import_module("routers.payment")
    try:
        result = payment_api.create_payment(schemas.PaymentCreate(booking_id=pending.id, method="mock"), db, {"username":user.username})
        assert result.status == models.PAYMENT_SUCCESS
        assert result.amount == 499
        booking = db.get(models.Booking, pending.id)
        assert booking.status == models.BOOKING_CONFIRMED and booking.payment_status == "paid"
        assert db.query(models.Ticket).filter_by(booking_id=pending.id, seat_id=seat_id).count() == 1
        retried = payment_api.create_payment(schemas.PaymentCreate(booking_id=pending.id, method="mock"), db, {"username":user.username})
        assert retried.id == result.id
        assert db.query(models.Payment).filter_by(booking_id=pending.id).count() == 1
    finally:
        sys.modules.pop("routers.payment", None)
