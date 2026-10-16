from datetime import datetime, timezone                                                                                 # UTC TIMESTAMP UTILITIES
import secrets                                                                                                           # SECURE TOKEN GENERATION
import uuid                                                                                                              # UNIQUE TICKET IDENTIFIERS
from typing import List, Optional                                                                                       # OPTIONAL/LIST TYPE HINTS

from fastapi import APIRouter, Depends, HTTPException, Request, status                                                  # FASTAPI ROUTING AND ERRORS
from pydantic import BaseModel, Field                                                                                   # REQUEST VALIDATION
from core.limiter import limiter                                                                                         # API RATE LIMITING
from sqlalchemy.orm import Session                                                                                       # SQLALCHEMY SESSION

import models                                                                                                             # DATABASE MODELS
import schemas                                                                                                            # GENERAL BOOKING SCHEMAS
import schemas_seating                                                                                                    # SEATING BOOKING SCHEMAS

from utils.helpers import get_db                                                                                          # DATABASE DEPENDENCY
from core.security import get_current_user                                                                                 # AUTHENTICATED USER DEPENDENCY
from services.booking_service import BookingService                                                                      # BOOKING LIFECYCLE ORCHESTRATION
from services.inventory_service import InventoryService
from services.booking_presenter import serialize_booking                                                                  # SAFE, LOCKED INVENTORY HOLDS


router = APIRouter()                                                                                                      # BOOKING ROUTER


def get_authenticated_user(user, db: Session):                                                                           # RESOLVE AUTHENTICATED DATABASE USER
    db_user = db.query(models.User).filter(models.User.username == user["username"]).first()                             # FIND USER BY JWT SUBJECT
    if not db_user:                                                                                                      # VALIDATE USER EXISTENCE
        raise HTTPException(status_code=404, detail="User not found")                                                   # RETURN USER NOT FOUND
    if not db_user.is_active:                                                                                             # VALIDATE ACCOUNT STATUS
        raise HTTPException(status_code=403, detail="User account is inactive")                                         # REJECT INACTIVE ACCOUNT
    return db_user                                                                                                       # RETURN DATABASE USER


def generate_ticket_code():                                                                                              # GENERATE UNIQUE PUBLIC TICKET CODE
    return f"EVT-{uuid.uuid4().hex[:16].upper()}"                                                                        # RETURN HUMAN-READABLE TICKET IDENTIFIER


def generate_qr_token():                                                                                                 # GENERATE SECURE QR VERIFICATION TOKEN
    return secrets.token_urlsafe(32)                                                                                      # RETURN NON-GUESSABLE QR TOKEN


class InventoryBookingRequest(BaseModel):                                                                                # UNIFIED CREATE+HOLD REQUEST FROM event-details.js
    event_id: int = Field(..., gt=0)                                                                                     # TARGET EVENT
    tickets: int = Field(default=1, ge=1, le=10)                                                                                # QUANTITY FOR ZONE/GENERAL - IGNORED FOR SEAT_IDS (LEN USED INSTEAD)
    seat_ids: Optional[List[int]] = Field(default=None, min_length=1, max_length=10)                                                                                 # FIXED-SEAT SELECTION
    zone_id: Optional[int] = Field(default=None, gt=0)                                                                                        # ZONE SELECTION
    ticket_type_id: Optional[int] = Field(default=None, gt=0)                                                                                 # PASS SELECTION
    idempotency_key: Optional[str] = Field(default=None, max_length=128)                                                                                # CLIENT-SUPPLIED IDEMPOTENCY KEY
    total_amount: Optional[int] = None                                                                                   # ACCEPTED FOR FRONTEND COMPATIBILITY - NEVER USED FOR PRICING; SERVER ALWAYS COMPUTES ITS OWN TOTAL


def _inventory_booking_response(booking: models.Booking) -> dict:
    return serialize_booking(booking, include_event=True)


@router.post("")                                                                                                         # CREATE + HOLD IN ONE CALL (matches event-details.js's POST /api/bookings exactly, no trailing slash)
@limiter.limit("10/minute")
def create_inventory_booking(request: Request, payload: InventoryBookingRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):  # UNIFIED HOLD ENTRY POINT
    db_user = get_authenticated_user(user, db)                                                                            # RESOLVE AUTHENTICATED USER

    if sum(bool(value) for value in (payload.seat_ids, payload.zone_id, payload.ticket_type_id)) != 1:
        raise HTTPException(status_code=400, detail="Select exactly one of seat_ids, zone_id or ticket_type_id")
    if payload.seat_ids and (len(payload.seat_ids) > 10 or len(set(payload.seat_ids)) != len(payload.seat_ids)):
        raise HTTPException(status_code=400, detail="Select 1-10 unique seats")
    if not (payload.seat_ids or payload.zone_id or payload.ticket_type_id):                                              # REQUIRE EXACTLY ONE INVENTORY SELECTION
        raise HTTPException(status_code=400, detail="Must specify seat_ids, zone_id, or ticket_type_id")                # REJECT AMBIGUOUS REQUEST

    event = db.get(models.Event, payload.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    selected_mode = (models.INVENTORY_SEAT if payload.seat_ids else
                     models.INVENTORY_ZONE if payload.zone_id else models.INVENTORY_GENERAL)
    if event.inventory_type != selected_mode:
        raise HTTPException(status_code=400, detail="Selection does not match event booking type")

    booking_service = BookingService(db)                                                                                 # LIFECYCLE ORCHESTRATION
    inventory_service = InventoryService(db)                                                                             # SAFE, LOCKED HOLD OPERATIONS

    try:                                                                                                                 # START HOLD SEQUENCE
        booking = booking_service.create_hold(                                                                          # CREATE OR REUSE (VIA IDEMPOTENCY KEY) A PENDING BOOKING
            user_id=db_user.id,
            event_id=payload.event_id,
            idempotency_key=payload.idempotency_key,
        )

        # Replaying a successful request must return its existing hold unchanged.
        if booking.status == models.BOOKING_HELD and booking.items:
            return _inventory_booking_response(booking)
        if booking.status != models.BOOKING_PENDING:
            raise ValueError("This booking cannot be modified")

        if payload.seat_ids:                                                                                            # FIXED-SEAT HOLD
            booking = inventory_service.hold_seats(
                event_id=payload.event_id,
                seat_ids=payload.seat_ids,
                user_id=db_user.id,
                booking_id=booking.id,
            )
        elif payload.zone_id:                                                                                           # ZONE HOLD
            booking = inventory_service.hold_zone(
                event_id=payload.event_id,
                zone_id=payload.zone_id,
                quantity=payload.tickets,
                user_id=db_user.id,
                booking_id=booking.id,
            )
        else:                                                                                                           # PASS HOLD
            booking = inventory_service.hold_passes(
                event_id=payload.event_id,
                ticket_type_id=payload.ticket_type_id,
                quantity=payload.tickets,
                user_id=db_user.id,
                booking_id=booking.id,
            )

        return _inventory_booking_response(booking)                                                                      # RETURN HELD BOOKING

    except ValueError as exc:                                                                                            # HANDLE EXPECTED BUSINESS ERRORS (sold out, expired, not found, etc.)
        db.rollback()                                                                                                    # ROLLBACK PARTIAL HOLD
        raise HTTPException(status_code=400, detail=str(exc))                                                           # RETURN CLEAR CLIENT ERROR


@router.get("/{booking_id}/status")                                                                                      # READ-ONLY HOLD-BASED BOOKING LOOKUP (used by a future checkout/confirmation page)
def get_inventory_booking(booking_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):              # FETCH OWNED BOOKING
    db_user = get_authenticated_user(user, db)                                                                            # RESOLVE AUTHENTICATED USER
    booking_service = BookingService(db)                                                                                 # LIFECYCLE ORCHESTRATION

    try:                                                                                                                 # START LOOKUP
        booking = booking_service.get_booking(booking_id=booking_id, user_id=db_user.id)                                # FETCH OWNED BOOKING
        return _inventory_booking_response(booking)                                                                      # RETURN BOOKING STATE
    except ValueError as exc:                                                                                            # HANDLE NOT FOUND / NOT OWNED
        raise HTTPException(status_code=404, detail=str(exc))                                                           # RETURN NOT FOUND


# Deprecated: these paths issued tickets without the unified 15-minute hold or
# a payment confirmation and could double-sell inventory. Keep a clear 410
# instead of silently letting old frontend clients bypass checkout.
@router.post("/book")
def deprecated_general_booking():
    raise HTTPException(status_code=410, detail="Use POST /api/bookings for a 15-minute inventory hold, then POST /api/payment/ for mock checkout")


@router.post("/book/seats")
def deprecated_seat_booking():
    raise HTTPException(status_code=410, detail="Use POST /api/bookings with seat_ids, then POST /api/payment/ for mock checkout")


@router.get("/my-bookings")
def my_bookings(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """A customer's complete orders, including issued ticket codes and pending checkout."""
    db_user = get_authenticated_user(user, db)
    bookings = (db.query(models.Booking).filter(models.Booking.user_id == db_user.id)
                .order_by(models.Booking.booking_time.desc()).all())
    return [serialize_booking(booking, include_event=True) for booking in bookings
            if booking.items or booking.tickets_rel]


@router.get("/{booking_id}/tickets")
def my_booking_tickets(booking_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = get_authenticated_user(user, db)
    booking = db.query(models.Booking).filter_by(id=booking_id, user_id=db_user.id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != models.BOOKING_CONFIRMED or booking.payment_status != "paid":
        raise HTTPException(status_code=409, detail="Tickets are issued only after successful payment")
    return serialize_booking(booking)["ticket_details"]


@router.delete("/book/{booking_id}")
def cancel_booking(booking_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Cancel an unpaid hold safely. Refund policy is required for paid bookings."""
    db_user = get_authenticated_user(user, db)
    booking = db.query(models.Booking).filter_by(id=booking_id, user_id=db_user.id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.payment_status == "paid" or booking.status == models.BOOKING_CONFIRMED:
        raise HTTPException(status_code=409, detail="Paid bookings require a verified refund workflow; cancellation is disabled in this demo")
    try:
        cancelled = BookingService(db).cancel_booking(booking_id, db_user.id)
        cancelled.payment_status = "cancelled"
        db.commit()
        return {"success": True, "booking_id": cancelled.id, "status": cancelled.status}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
