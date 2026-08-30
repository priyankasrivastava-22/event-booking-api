"""
Booking service - orchestrates the Booking lifecycle around InventoryService.

InventoryService owns *what's held* (seats/zones/passes). BookingService owns
the Booking record's own lifecycle and, on confirm, issues the actual
redeemable Ticket rows. It does not duplicate any locking/availability logic
- every mutation to inventory goes through InventoryService.

NOT YET WIRED IN (by design, per current project decision):
- routers/bookings.py still has its own separate booking-creation flow.
  This service is a standalone addition for now; wiring bookings.py to call
  into it is a deliberate later step, not done here.
- confirm_booking() is meant to be called once payment has actually
  succeeded (e.g. from payment.py after a successful charge). It is not
  wired into payment.py yet either - calling it prematurely would issue
  tickets for an unpaid booking.
"""

from datetime import datetime, timezone
import secrets
import uuid
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
from services.inventory_service import InventoryService


def generate_ticket_code() -> str:
    # Matches routers/bookings.py's generator exactly, so ticket codes look
    # identical regardless of which code path issued them.
    return f"EVT-{uuid.uuid4().hex[:16].upper()}"


def generate_qr_token() -> str:
    return secrets.token_urlsafe(32)


class BookingService:
    def __init__(self, db: Session):
        self.db = db
        self.inventory = InventoryService(db)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _get_event(self, event_id: int) -> models.Event:
        event = self.db.query(models.Event).filter(models.Event.id == event_id).first()
        if not event:
            raise ValueError("Event not found")
        return event

    def _get_owned_booking(self, booking_id: int, user_id: int, lock: bool = True) -> models.Booking:
        query = self.db.query(models.Booking).filter(models.Booking.id == booking_id)
        if lock:
            query = query.with_for_update()
        booking = query.first()
        if not booking:
            raise ValueError("Booking not found")
        if booking.user_id != user_id:
            raise ValueError("This booking does not belong to the current user")
        return booking

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_hold(self, user_id: int, event_id: int, idempotency_key: Optional[str] = None) -> models.Booking:
        """Create a new empty (pending, no items yet) booking for a user to
        start adding seats/zone/pass holds to via InventoryService.

        Idempotency: if idempotency_key is supplied and a booking already
        exists with that key, that existing booking is returned unchanged
        instead of creating a new one - safe for a client to retry a
        "start checkout" request without risking a duplicate booking.
        """
        self._get_event(event_id)

        if idempotency_key:
            existing = (
                self.db.query(models.Booking)
                .filter(models.Booking.idempotency_key == idempotency_key)
                .first()
            )
            if existing:
                if existing.user_id != user_id:
                    raise ValueError("This idempotency key was already used by a different user")
                return existing

        booking = models.Booking(
            user_id=user_id,
            event_id=event_id,
            tickets=0,
            status=models.BOOKING_PENDING,
            total_amount=0,
            idempotency_key=idempotency_key,
            payment_status="pending",
        )
        self.db.add(booking)

        try:
            self.db.commit()
        except IntegrityError:
            # Concurrent request raced us with the same idempotency_key and
            # committed first - fetch and return their row instead of failing.
            self.db.rollback()
            if idempotency_key:
                existing = (
                    self.db.query(models.Booking)
                    .filter(models.Booking.idempotency_key == idempotency_key)
                    .first()
                )
                if existing:
                    return existing
            raise ValueError("Could not create booking - please try again")

        self.db.refresh(booking)
        return booking

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_booking(self, booking_id: int, user_id: int) -> models.Booking:
        booking = self._get_owned_booking(booking_id, user_id, lock=False)
        return booking

    # ------------------------------------------------------------------
    # Confirm - call AFTER payment has succeeded
    # ------------------------------------------------------------------

    def confirm_booking(self, booking_id: int, user_id: int) -> models.Booking:
        """Lock in held inventory as sold (via InventoryService) and issue a
        Ticket row for every unit purchased. Intended to run after payment
        has actually succeeded - it does not check payment status itself,
        since that decision belongs to whatever calls this (e.g. payment.py)."""
        booking = self.inventory.confirm_inventory(booking_id=booking_id, user_id=user_id)

        # confirm_inventory() already validated ownership/state and flipped
        # inventory + booking + items to confirmed. Now issue tickets.
        items = (
            self.db.query(models.BookingItem)
            .filter(
                models.BookingItem.booking_id == booking.id,
                models.BookingItem.status == models.BOOKING_CONFIRMED,
            )
            .all()
        )

        now = self._now()

        for item in items:
            inventory = (
                self.db.query(models.Inventory)
                .filter(models.Inventory.id == item.inventory_id)
                .first()
            )
            if not inventory:
                continue

            # One Ticket per unit purchased - quantity many for pooled
            # zone/pass items, exactly one for a seat item.
            for _ in range(item.quantity):
                self.db.add(models.Ticket(
                    booking_id=booking.id,
                    event_id=booking.event_id,
                    seat_id=inventory.seat_id,
                    zone_id=inventory.zone_id,
                    ticket_type_id=inventory.ticket_type_id,
                    ticket_code=generate_ticket_code(),
                    qr_token=generate_qr_token(),
                    price_paid=item.price,
                    status=models.TICKET_CONFIRMED,
                    created_at=now,
                ))

        self.db.commit()
        self.db.refresh(booking)
        return booking

    # ------------------------------------------------------------------
    # Expire - release a single booking's hold (admin/manual use;
    # release_expired_holds() in InventoryService is the bulk sweep)
    # ------------------------------------------------------------------

    def expire_booking(self, booking_id: int) -> models.Booking:
        booking = (
            self.db.query(models.Booking)
            .filter(models.Booking.id == booking_id)
            .with_for_update()
            .first()
        )
        if not booking:
            raise ValueError("Booking not found")

        if booking.status not in (models.BOOKING_PENDING, models.BOOKING_HELD):
            raise ValueError(f"Booking is '{booking.status}' and cannot be expired")

        self._release_all_items(booking)

        booking.status = models.BOOKING_EXPIRED
        booking.expires_at = None

        self.db.commit()
        self.db.refresh(booking)
        return booking

    # ------------------------------------------------------------------
    # Cancel - user-initiated
    # ------------------------------------------------------------------

    def cancel_booking(self, booking_id: int, user_id: int) -> models.Booking:
        booking = self._get_owned_booking(booking_id, user_id)

        if booking.status in (models.BOOKING_CANCELLED, models.BOOKING_EXPIRED):
            raise ValueError(f"Booking is already '{booking.status}'")

        was_confirmed = booking.status == models.BOOKING_CONFIRMED

        self._release_all_items(booking)

        if was_confirmed:
            # Tickets already existed for a confirmed booking - cancel them too.
            tickets = (
                self.db.query(models.Ticket)
                .filter(
                    models.Ticket.booking_id == booking.id,
                    models.Ticket.status != models.TICKET_CANCELLED,
                )
                .all()
            )
            for ticket in tickets:
                ticket.status = models.TICKET_CANCELLED
            # NOTE: this does not trigger a refund - a paid, confirmed booking
            # being cancelled needs a real refund flow (payment gateway call)
            # which is outside this service's scope. payment_status is left
            # as "paid" here deliberately so it isn't silently misreported;
            # handle the refund explicitly wherever cancellation for a paid
            # booking is triggered from.

        booking.status = models.BOOKING_CANCELLED
        booking.expires_at = None

        self.db.commit()
        self.db.refresh(booking)
        return booking

    # ------------------------------------------------------------------
    # Shared release helper
    # ------------------------------------------------------------------

    def _release_all_items(self, booking: models.Booking) -> None:
        """Release every still-held item on a booking, regardless of type,
        by delegating to InventoryService's release methods (which already
        know how to correctly unwind seats vs. zone/pass counters)."""
        has_seat = (
            self.db.query(models.BookingItem)
            .join(models.Inventory, models.BookingItem.inventory_id == models.Inventory.id)
            .filter(
                models.BookingItem.booking_id == booking.id,
                models.BookingItem.status == models.BOOKING_HELD,
                models.Inventory.inventory_type == models.INVENTORY_SEAT,
            )
            .first()
            is not None
        )
        has_zone = (
            self.db.query(models.BookingItem)
            .join(models.Inventory, models.BookingItem.inventory_id == models.Inventory.id)
            .filter(
                models.BookingItem.booking_id == booking.id,
                models.BookingItem.status == models.BOOKING_HELD,
                models.Inventory.inventory_type == models.INVENTORY_ZONE,
            )
            .first()
            is not None
        )
        has_pass = (
            self.db.query(models.BookingItem)
            .join(models.Inventory, models.BookingItem.inventory_id == models.Inventory.id)
            .filter(
                models.BookingItem.booking_id == booking.id,
                models.BookingItem.status == models.BOOKING_HELD,
                models.Inventory.inventory_type == models.INVENTORY_GENERAL,
            )
            .first()
            is not None
        )

        if has_seat:
            self.inventory.release_seats(booking_id=booking.id, user_id=booking.user_id, commit=False)
        if has_zone:
            self.inventory.release_zone(booking_id=booking.id, user_id=booking.user_id, commit=False)
        if has_pass:
            self.inventory.release_passes(booking_id=booking.id, user_id=booking.user_id, commit=False)