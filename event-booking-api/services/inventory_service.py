"""
Inventory service  - the single authoritative layer for holding, releasing,
and confirming sellable inventory (fixed seats, GA zone slots, and
general-admission passes) against a Booking.

DESIGN NOTES (read this before touching hold/release/confirm logic):

1. Concurrency: every mutation locks the relevant row(s) with
   SELECT ... FOR UPDATE inside the current transaction *before* checking
   availability, so two simultaneous requests for the same seat/zone/pass
   can never both succeed. This is the "strong consistency" approach
   (chosen over optimistic locking) to guarantee no double-booking.

2. Seats vs. pooled inventory (zone / pass) are handled differently:
   - SEAT: each physical Seat has exactly one Inventory row (1:1, enforced
     by a unique constraint on Inventory.seat_id). That row's own
     status/lock_token/locked_until IS the authority for that one seat.
   - ZONE / GENERAL (pass): many bookings can simultaneously hold
     different quantities from the same pooled resource, so a single
     shared Inventory row's status/locked_until can't represent multiple
     concurrent per-booking holds with different expiry times. The real
     authority for these is the counters on EventZone (capacity /
     sold_count / locked_count) and TicketType (inventory_limit /
     sold_count / locked_count), combined with the owning Booking's own
     expires_at. The shared Inventory row for these types exists only so
     BookingItem.inventory_id has something stable to reference, and its
     `status` field is kept as a best-effort *display* summary, not a gate.

3. Expiration has two complementary mechanisms (per project decision):
   - Lazy release: any time this service touches a locked SEAT inventory
     row and finds its hold already expired, it releases it immediately
     before evaluating availability.
   - Background sweep: release_expired_holds() finds every Booking whose
     hold has expired and releases everything it was holding. Meant to be
     called periodically by jobs/inventory_cleanup.py.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
import uuid

from sqlalchemy.orm import Session

import models
from inventory_config import INVENTORY_HOLD_MINUTES


class InventoryService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Small internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _hold_expiry(self) -> datetime:
        return self._now() + timedelta(minutes=INVENTORY_HOLD_MINUTES)

    @staticmethod
    def _new_lock_token() -> str:
        return uuid.uuid4().hex

    def _get_event(self, event_id: int) -> models.Event:
        event = self.db.query(models.Event).filter(models.Event.id == event_id).first()
        if not event:
            raise ValueError("Event not found")
        return event

    def _get_owned_booking(self, booking_id: int, user_id: int) -> models.Booking:
        booking = (
            self.db.query(models.Booking)
            .filter(models.Booking.id == booking_id)
            .with_for_update()
            .first()
        )
        if not booking:
            raise ValueError("Booking not found")
        if booking.user_id != user_id:
            raise ValueError("This booking does not belong to the current user")
        return booking

    def _assert_booking_holdable(self, booking: models.Booking, event_id: int) -> None:
        if booking.event_id != event_id:
            raise ValueError("Booking does not belong to this event")
        if booking.status not in (models.BOOKING_PENDING, models.BOOKING_HELD):
            raise ValueError(f"Booking is '{booking.status}' and can no longer be modified")

    def _existing_item(self, booking_id: int, inventory_id: int) -> Optional[models.BookingItem]:
        return (
            self.db.query(models.BookingItem)
            .filter(
                models.BookingItem.booking_id == booking_id,
                models.BookingItem.inventory_id == inventory_id,
            )
            .with_for_update()
            .first()
        )

    def _maybe_close_booking(self, booking: models.Booking) -> None:
        """If a booking has no held items left after a release, drop it back
        to pending (empty cart) instead of leaving it stuck as 'held'."""
        remaining = (
            self.db.query(models.BookingItem)
            .filter(
                models.BookingItem.booking_id == booking.id,
                models.BookingItem.status == models.BOOKING_HELD,
            )
            .count()
        )
        if remaining == 0 and booking.status == models.BOOKING_HELD:
            booking.status = models.BOOKING_PENDING
            booking.expires_at = None

    # -- seat-specific release (seat inventory IS the authority) --------

    def _release_seat_inventory(self, inventory: models.Inventory) -> None:
        inventory.status = models.INVENTORY_AVAILABLE
        inventory.lock_token = None
        inventory.locked_until = None
        inventory.updated_at = self._now()

        if inventory.seat_id:
            seat = (
                self.db.query(models.Seat)
                .filter(models.Seat.id == inventory.seat_id)
                .with_for_update()
                .first()
            )
            if seat and seat.status == models.SEAT_LOCKED:
                seat.status = models.SEAT_AVAILABLE

            active_lock = (
                self.db.query(models.SeatLock)
                .filter(
                    models.SeatLock.seat_id == inventory.seat_id,
                    models.SeatLock.status == models.LOCK_ACTIVE,
                )
                .order_by(models.SeatLock.id.desc())
                .with_for_update()
                .first()
            )
            if active_lock:
                active_lock.status = models.LOCK_RELEASED
                active_lock.released_at = self._now()

    def _lazy_release_seat_if_expired(self, inventory: models.Inventory) -> bool:
        """Only meaningful for SEAT-type rows  - pooled (zone/pass) rows don't
        carry a single authoritative expiry (see module docstring)."""
        if inventory.inventory_type != models.INVENTORY_SEAT:
            return False
        if (
            inventory.status == models.INVENTORY_LOCKED
            and inventory.locked_until is not None
            and inventory.locked_until <= self._now()
        ):
            self._release_seat_inventory(inventory)
            return True
        return False

    # -- pooled (zone / pass) display-status sync ------------------------

    @staticmethod
    def _sync_zone_inventory_status(inventory: models.Inventory, zone: models.EventZone) -> None:
        if zone.sold_count >= zone.capacity and zone.capacity > 0:
            inventory.status = models.INVENTORY_SOLD
        elif zone.locked_count > 0:
            inventory.status = models.INVENTORY_LOCKED
        else:
            inventory.status = models.INVENTORY_AVAILABLE

    @staticmethod
    def _sync_ticket_type_inventory_status(inventory: models.Inventory, ticket_type: models.TicketType) -> None:
        if ticket_type.inventory_limit is not None and ticket_type.sold_count >= ticket_type.inventory_limit:
            inventory.status = models.INVENTORY_SOLD
        elif ticket_type.locked_count > 0:
            inventory.status = models.INVENTORY_LOCKED
        else:
            inventory.status = models.INVENTORY_AVAILABLE

    def _get_or_create_zone_inventory(self, event_id: int, zone: models.EventZone) -> models.Inventory:
        # zone is already locked (FOR UPDATE) by the caller before this runs,
        # so concurrent first-time holds on the same zone naturally serialize
        # here and can't create duplicate rows.
        inventory = (
            self.db.query(models.Inventory)
            .filter(
                models.Inventory.zone_id == zone.id,
                models.Inventory.inventory_type == models.INVENTORY_ZONE,
            )
            .with_for_update()
            .first()
        )
        if not inventory:
            inventory = models.Inventory(
                event_id=event_id,
                inventory_type=models.INVENTORY_ZONE,
                status=models.INVENTORY_AVAILABLE,
                price=zone.base_price,
                zone_id=zone.id,
            )
            self.db.add(inventory)
            self.db.flush()
        return inventory

    def _get_or_create_ticket_type_inventory(self, event_id: int, ticket_type: models.TicketType) -> models.Inventory:
        # ticket_type is already locked (FOR UPDATE) by the caller, so this
        # is race-free for the same reason as the zone case above.
        inventory = (
            self.db.query(models.Inventory)
            .filter(models.Inventory.ticket_type_id == ticket_type.id)
            .with_for_update()
            .first()
        )
        if not inventory:
            inventory = models.Inventory(
                event_id=event_id,
                inventory_type=models.INVENTORY_GENERAL,
                status=models.INVENTORY_AVAILABLE,
                price=ticket_type.price,
                ticket_type_id=ticket_type.id,
            )
            self.db.add(inventory)
            self.db.flush()
        return inventory

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_event_inventory(self, event_id: int) -> List[models.Inventory]:
        self._get_event(event_id)

        rows = (
            self.db.query(models.Inventory)
            .filter(models.Inventory.event_id == event_id)
            .all()
        )

        released_any = False
        for row in rows:
            if self._lazy_release_seat_if_expired(row):
                released_any = True
        if released_any:
            self.db.commit()

        return rows

    # ------------------------------------------------------------------
    # Validation (advisory, non-locking pre-check)
    # ------------------------------------------------------------------

    def validate_inventory(
        self,
        event_id: int,
        inventory_type: str,
        seat_ids: Optional[List[int]] = None,
        zone_id: Optional[int] = None,
        ticket_type_id: Optional[int] = None,
        quantity: Optional[int] = None,
    ) -> bool:
        """Best-effort availability check with no row locks  - useful for a
        UI to show "still available" before the user commits to a hold.
        This is advisory only; hold_*() re-validates under lock and is the
        real authority."""
        self._get_event(event_id)
        now = self._now()

        if inventory_type == models.INVENTORY_SEAT:
            if not seat_ids:
                raise ValueError("seat_ids is required for seat inventory")
            for seat_id in seat_ids:
                seat = (
                    self.db.query(models.Seat)
                    .filter(models.Seat.id == seat_id, models.Seat.event_id == event_id)
                    .first()
                )
                if not seat:
                    raise ValueError(f"Seat {seat_id} not found for this event")
                if not seat.is_active:
                    raise ValueError(f"Seat {seat.seat_code} is not available for sale")
                inv = seat.inventory
                if not inv:
                    raise ValueError(f"Seat {seat.seat_code} has no inventory record")
                expired = (
                    inv.status == models.INVENTORY_LOCKED
                    and inv.locked_until is not None
                    and inv.locked_until <= now
                )
                if inv.status != models.INVENTORY_AVAILABLE and not expired:
                    raise ValueError(f"Seat {seat.seat_code} is currently unavailable")

        elif inventory_type == models.INVENTORY_ZONE:
            if not zone_id:
                raise ValueError("zone_id is required for zone inventory")
            if not quantity or quantity <= 0:
                raise ValueError("quantity must be a positive number")
            zone = (
                self.db.query(models.EventZone)
                .filter(models.EventZone.id == zone_id, models.EventZone.event_id == event_id)
                .first()
            )
            if not zone:
                raise ValueError("Zone not found for this event")
            if not zone.is_active:
                raise ValueError(f"Zone {zone.name} is not available for sale")
            available = zone.capacity - zone.sold_count - zone.locked_count
            if available < quantity:
                raise ValueError(f"Only {max(available, 0)} seat(s) left in zone {zone.name}")

        elif inventory_type == models.INVENTORY_GENERAL:
            if not ticket_type_id:
                raise ValueError("ticket_type_id is required for pass inventory")
            if not quantity or quantity <= 0:
                raise ValueError("quantity must be a positive number")
            ticket_type = (
                self.db.query(models.TicketType)
                .filter(models.TicketType.id == ticket_type_id, models.TicketType.event_id == event_id)
                .first()
            )
            if not ticket_type:
                raise ValueError("Ticket type not found for this event")
            if not ticket_type.is_active:
                raise ValueError(f"Pass {ticket_type.name} is not available for sale")
            if ticket_type.inventory_limit is not None:
                available = ticket_type.inventory_limit - ticket_type.sold_count - ticket_type.locked_count
                if available < quantity:
                    raise ValueError(f"Only {max(available, 0)} '{ticket_type.name}' pass(es) left")

        else:
            raise ValueError(f"Unknown inventory_type: {inventory_type}")

        return True

    # ------------------------------------------------------------------
    # Hold
    # ------------------------------------------------------------------

    def hold_seats(self, event_id: int, seat_ids: List[int], user_id: int, booking_id: int) -> models.Booking:
        if not seat_ids:
            raise ValueError("seat_ids is required")
        if len(set(seat_ids)) != len(seat_ids):
            raise ValueError("Duplicate seat_ids in request")

        self._get_event(event_id)
        booking = self._get_owned_booking(booking_id, user_id)
        self._assert_booking_holdable(booking, event_id)

        now = self._now()
        expiry = self._hold_expiry()
        locked_pairs = []

        # Lock every requested seat + its inventory row, in a stable id
        # order, BEFORE validating anything. Stable ordering avoids
        # deadlocks against a concurrent request holding overlapping seats
        # in a different order.
        for seat_id in sorted(set(seat_ids)):
            seat = (
                self.db.query(models.Seat)
                .filter(models.Seat.id == seat_id, models.Seat.event_id == event_id)
                .with_for_update()
                .first()
            )
            if not seat:
                raise ValueError(f"Seat {seat_id} not found for this event")
            if not seat.is_active:
                raise ValueError(f"Seat {seat.seat_code} is not available for sale")

            inventory = (
                self.db.query(models.Inventory)
                .filter(models.Inventory.seat_id == seat.id)
                .with_for_update()
                .first()
            )
            if not inventory:
                raise ValueError(f"Seat {seat.seat_code} has no inventory record")

            self._lazy_release_seat_if_expired(inventory)

            if inventory.status != models.INVENTORY_AVAILABLE:
                raise ValueError(f"Seat {seat.seat_code} is no longer available")

            if self._existing_item(booking.id, inventory.id):
                raise ValueError(f"Seat {seat.seat_code} is already held in this booking")

            locked_pairs.append((seat, inventory))

        # Every requested seat is validated and locked  - now mutate.
        total_added = 0
        for seat, inventory in locked_pairs:
            inventory.status = models.INVENTORY_LOCKED
            inventory.lock_token = self._new_lock_token()
            inventory.locked_until = expiry
            inventory.updated_at = now

            seat.status = models.SEAT_LOCKED

            self.db.add(models.SeatLock(
                seat_id=seat.id,
                user_id=user_id,
                lock_token=inventory.lock_token,
                locked_at=now,
                expires_at=expiry,
                status=models.LOCK_ACTIVE,
            ))

            self.db.add(models.BookingItem(
                booking_id=booking.id,
                inventory_id=inventory.id,
                quantity=1,
                price=seat.price,
                status=models.BOOKING_HELD,
            ))

            total_added += seat.price

        booking.total_amount = (booking.total_amount or 0) + total_added
        booking.expires_at = expiry
        booking.status = models.BOOKING_HELD

        self.db.commit()
        self.db.refresh(booking)
        return booking

    def hold_zone(self, event_id: int, zone_id: int, quantity: int, user_id: int, booking_id: int) -> models.Booking:
        if quantity is None or quantity <= 0:
            raise ValueError("quantity must be a positive number")

        self._get_event(event_id)
        booking = self._get_owned_booking(booking_id, user_id)
        self._assert_booking_holdable(booking, event_id)

        zone = (
            self.db.query(models.EventZone)
            .filter(models.EventZone.id == zone_id, models.EventZone.event_id == event_id)
            .with_for_update()
            .first()
        )
        if not zone:
            raise ValueError("Zone not found for this event")
        if not zone.is_active:
            raise ValueError(f"Zone {zone.name} is not available for sale")

        available = zone.capacity - zone.sold_count - zone.locked_count
        if available < quantity:
            raise ValueError(f"Only {max(available, 0)} seat(s) left in zone {zone.name}")

        inventory = self._get_or_create_zone_inventory(event_id, zone)

        zone.locked_count += quantity
        self._sync_zone_inventory_status(inventory, zone)
        inventory.updated_at = self._now()

        existing_item = self._existing_item(booking.id, inventory.id)
        if existing_item:
            existing_item.quantity += quantity
        else:
            self.db.add(models.BookingItem(
                booking_id=booking.id,
                inventory_id=inventory.id,
                quantity=quantity,
                price=zone.base_price,
                status=models.BOOKING_HELD,
            ))

        booking.total_amount = (booking.total_amount or 0) + (zone.base_price * quantity)
        booking.expires_at = self._hold_expiry()
        booking.status = models.BOOKING_HELD

        self.db.commit()
        self.db.refresh(booking)
        return booking

    def hold_passes(self, event_id: int, ticket_type_id: int, quantity: int, user_id: int, booking_id: int) -> models.Booking:
        if quantity is None or quantity <= 0:
            raise ValueError("quantity must be a positive number")

        self._get_event(event_id)
        booking = self._get_owned_booking(booking_id, user_id)
        self._assert_booking_holdable(booking, event_id)

        ticket_type = (
            self.db.query(models.TicketType)
            .filter(models.TicketType.id == ticket_type_id, models.TicketType.event_id == event_id)
            .with_for_update()
            .first()
        )
        if not ticket_type:
            raise ValueError("Ticket type not found for this event")
        if not ticket_type.is_active:
            raise ValueError(f"Pass {ticket_type.name} is not available for sale")

        if ticket_type.inventory_limit is not None:
            available = ticket_type.inventory_limit - ticket_type.sold_count - ticket_type.locked_count
            if available < quantity:
                raise ValueError(f"Only {max(available, 0)} '{ticket_type.name}' pass(es) left")

        inventory = self._get_or_create_ticket_type_inventory(event_id, ticket_type)

        ticket_type.locked_count += quantity
        self._sync_ticket_type_inventory_status(inventory, ticket_type)
        inventory.updated_at = self._now()

        existing_item = self._existing_item(booking.id, inventory.id)
        if existing_item:
            existing_item.quantity += quantity
        else:
            self.db.add(models.BookingItem(
                booking_id=booking.id,
                inventory_id=inventory.id,
                quantity=quantity,
                price=ticket_type.price,
                status=models.BOOKING_HELD,
            ))

        booking.total_amount = (booking.total_amount or 0) + (ticket_type.price * quantity)
        booking.expires_at = self._hold_expiry()
        booking.status = models.BOOKING_HELD

        self.db.commit()
        self.db.refresh(booking)
        return booking

    # ------------------------------------------------------------------
    # Release
    # ------------------------------------------------------------------

    def release_seats(self, booking_id: int, user_id: int, commit: bool = True) -> int:
        booking = self._get_owned_booking(booking_id, user_id)

        items = (
            self.db.query(models.BookingItem)
            .join(models.Inventory, models.BookingItem.inventory_id == models.Inventory.id)
            .filter(
                models.BookingItem.booking_id == booking.id,
                models.BookingItem.status == models.BOOKING_HELD,
                models.Inventory.inventory_type == models.INVENTORY_SEAT,
            )
            .with_for_update()
            .all()
        )

        released = 0
        for item in items:
            inventory = (
                self.db.query(models.Inventory)
                .filter(models.Inventory.id == item.inventory_id)
                .with_for_update()
                .first()
            )
            if inventory:
                self._release_seat_inventory(inventory)
            item.status = models.BOOKING_CANCELLED
            released += item.quantity

        self._maybe_close_booking(booking)
        if commit:
            self.db.commit()
        return released

    def release_zone(self, booking_id: int, user_id: int, commit: bool = True) -> int:
        booking = self._get_owned_booking(booking_id, user_id)

        items = (
            self.db.query(models.BookingItem)
            .join(models.Inventory, models.BookingItem.inventory_id == models.Inventory.id)
            .filter(
                models.BookingItem.booking_id == booking.id,
                models.BookingItem.status == models.BOOKING_HELD,
                models.Inventory.inventory_type == models.INVENTORY_ZONE,
            )
            .with_for_update()
            .all()
        )

        released = 0
        for item in items:
            inventory = (
                self.db.query(models.Inventory)
                .filter(models.Inventory.id == item.inventory_id)
                .with_for_update()
                .first()
            )
            if inventory and inventory.zone_id:
                zone = (
                    self.db.query(models.EventZone)
                    .filter(models.EventZone.id == inventory.zone_id)
                    .with_for_update()
                    .first()
                )
                if zone:
                    zone.locked_count = max(0, zone.locked_count - item.quantity)
                    self._sync_zone_inventory_status(inventory, zone)
                    inventory.updated_at = self._now()

            item.status = models.BOOKING_CANCELLED
            released += item.quantity

        self._maybe_close_booking(booking)
        if commit:
            self.db.commit()
        return released

    def release_passes(self, booking_id: int, user_id: int, commit: bool = True) -> int:
        booking = self._get_owned_booking(booking_id, user_id)

        items = (
            self.db.query(models.BookingItem)
            .join(models.Inventory, models.BookingItem.inventory_id == models.Inventory.id)
            .filter(
                models.BookingItem.booking_id == booking.id,
                models.BookingItem.status == models.BOOKING_HELD,
                models.Inventory.inventory_type == models.INVENTORY_GENERAL,
            )
            .with_for_update()
            .all()
        )

        released = 0
        for item in items:
            inventory = (
                self.db.query(models.Inventory)
                .filter(models.Inventory.id == item.inventory_id)
                .with_for_update()
                .first()
            )
            if inventory and inventory.ticket_type_id:
                ticket_type = (
                    self.db.query(models.TicketType)
                    .filter(models.TicketType.id == inventory.ticket_type_id)
                    .with_for_update()
                    .first()
                )
                if ticket_type:
                    ticket_type.locked_count = max(0, ticket_type.locked_count - item.quantity)
                    self._sync_ticket_type_inventory_status(inventory, ticket_type)
                    inventory.updated_at = self._now()

            item.status = models.BOOKING_CANCELLED
            released += item.quantity

        self._maybe_close_booking(booking)
        if commit:
            self.db.commit()
        return released

    # ------------------------------------------------------------------
    # Confirm
    # ------------------------------------------------------------------

    def confirm_inventory(self, booking_id: int, user_id: int) -> models.Booking:
        booking = self._get_owned_booking(booking_id, user_id)

        if booking.status == models.BOOKING_CONFIRMED:
            raise ValueError("Booking is already confirmed")
        if booking.status != models.BOOKING_HELD:
            raise ValueError(f"Booking must be in 'held' state to confirm (currently '{booking.status}')")
        if booking.expires_at and booking.expires_at <= self._now():
            raise ValueError("Hold has expired  - please select inventory again")

        items = (
            self.db.query(models.BookingItem)
            .filter(
                models.BookingItem.booking_id == booking.id,
                models.BookingItem.status == models.BOOKING_HELD,
            )
            .with_for_update()
            .all()
        )
        if not items:
            raise ValueError("Booking has no held inventory to confirm")

        now = self._now()

        for item in items:
            inventory = (
                self.db.query(models.Inventory)
                .filter(models.Inventory.id == item.inventory_id)
                .with_for_update()
                .first()
            )
            if not inventory:
                raise ValueError("Inventory record missing for a booking item")

            if inventory.inventory_type == models.INVENTORY_SEAT:
                if inventory.status != models.INVENTORY_LOCKED or inventory.lock_token is None:
                    raise ValueError("A held seat is no longer locked  - please select again")
                if inventory.locked_until and inventory.locked_until <= now:
                    raise ValueError("Hold has expired  - please select inventory again")

                inventory.status = models.INVENTORY_SOLD
                inventory.lock_token = None
                inventory.locked_until = None
                inventory.updated_at = now

                if inventory.seat_id:
                    seat = (
                        self.db.query(models.Seat)
                        .filter(models.Seat.id == inventory.seat_id)
                        .with_for_update()
                        .first()
                    )
                    if seat:
                        seat.status = models.SEAT_SOLD
                    active_lock = (
                        self.db.query(models.SeatLock)
                        .filter(
                            models.SeatLock.seat_id == inventory.seat_id,
                            models.SeatLock.status == models.LOCK_ACTIVE,
                        )
                        .order_by(models.SeatLock.id.desc())
                        .with_for_update()
                        .first()
                    )
                    if active_lock:
                        active_lock.status = models.LOCK_CONVERTED
                        active_lock.released_at = now

            elif inventory.inventory_type == models.INVENTORY_ZONE and inventory.zone_id:
                zone = (
                    self.db.query(models.EventZone)
                    .filter(models.EventZone.id == inventory.zone_id)
                    .with_for_update()
                    .first()
                )
                if zone:
                    zone.locked_count = max(0, zone.locked_count - item.quantity)
                    zone.sold_count += item.quantity
                    self._sync_zone_inventory_status(inventory, zone)
                    inventory.updated_at = now

            elif inventory.inventory_type == models.INVENTORY_GENERAL and inventory.ticket_type_id:
                ticket_type = (
                    self.db.query(models.TicketType)
                    .filter(models.TicketType.id == inventory.ticket_type_id)
                    .with_for_update()
                    .first()
                )
                if ticket_type:
                    ticket_type.locked_count = max(0, ticket_type.locked_count - item.quantity)
                    ticket_type.sold_count += item.quantity
                    self._sync_ticket_type_inventory_status(inventory, ticket_type)
                    inventory.updated_at = now

            item.status = models.BOOKING_CONFIRMED

        booking.status = models.BOOKING_CONFIRMED
        booking.expires_at = None

        self.db.commit()
        self.db.refresh(booking)
        return booking

    # ------------------------------------------------------------------
    # Expiration sweep  - background job entry point
    # ------------------------------------------------------------------

    def release_expired_holds(self, batch_size: int = 100) -> int:
        """Find bookings whose hold has expired and release everything they
        were holding. Safe to call repeatedly / from multiple workers: uses
        SELECT ... FOR UPDATE SKIP LOCKED so overlapping sweeps never
        double-process the same booking."""
        now = self._now()

        expired_bookings = (
            self.db.query(models.Booking)
            .filter(
                models.Booking.status == models.BOOKING_HELD,
                models.Booking.expires_at.isnot(None),
                models.Booking.expires_at <= now,
            )
            .with_for_update(skip_locked=True)
            .limit(batch_size)
            .all()
        )

        released_count = 0

        for booking in expired_bookings:
            items = (
                self.db.query(models.BookingItem)
                .filter(
                    models.BookingItem.booking_id == booking.id,
                    models.BookingItem.status == models.BOOKING_HELD,
                )
                .with_for_update()
                .all()
            )

            for item in items:
                inventory = (
                    self.db.query(models.Inventory)
                    .filter(models.Inventory.id == item.inventory_id)
                    .with_for_update()
                    .first()
                )
                if inventory:
                    if inventory.inventory_type == models.INVENTORY_SEAT:
                        self._release_seat_inventory(inventory)

                    elif inventory.inventory_type == models.INVENTORY_ZONE and inventory.zone_id:
                        zone = (
                            self.db.query(models.EventZone)
                            .filter(models.EventZone.id == inventory.zone_id)
                            .with_for_update()
                            .first()
                        )
                        if zone:
                            zone.locked_count = max(0, zone.locked_count - item.quantity)
                            self._sync_zone_inventory_status(inventory, zone)
                            inventory.updated_at = now

                    elif inventory.inventory_type == models.INVENTORY_GENERAL and inventory.ticket_type_id:
                        ticket_type = (
                            self.db.query(models.TicketType)
                            .filter(models.TicketType.id == inventory.ticket_type_id)
                            .with_for_update()
                            .first()
                        )
                        if ticket_type:
                            ticket_type.locked_count = max(0, ticket_type.locked_count - item.quantity)
                            self._sync_ticket_type_inventory_status(inventory, ticket_type)
                            inventory.updated_at = now

                item.status = models.BOOKING_EXPIRED

            booking.status = models.BOOKING_EXPIRED
            released_count += 1

        self.db.commit()
        return released_count