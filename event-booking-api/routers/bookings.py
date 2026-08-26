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
from services.inventory_service import InventoryService                                                                  # SAFE, LOCKED INVENTORY HOLDS


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
    tickets: int = Field(default=1, gt=0)                                                                                # QUANTITY FOR ZONE/GENERAL - IGNORED FOR SEAT_IDS (LEN USED INSTEAD)
    seat_ids: Optional[List[int]] = None                                                                                 # FIXED-SEAT SELECTION
    zone_id: Optional[int] = None                                                                                        # ZONE SELECTION
    ticket_type_id: Optional[int] = None                                                                                 # PASS SELECTION
    idempotency_key: Optional[str] = None                                                                                # CLIENT-SUPPLIED IDEMPOTENCY KEY
    total_amount: Optional[int] = None                                                                                   # ACCEPTED FOR FRONTEND COMPATIBILITY - NEVER USED FOR PRICING; SERVER ALWAYS COMPUTES ITS OWN TOTAL


def _inventory_booking_response(booking: models.Booking) -> dict:                                                        # SERIALIZE BOOKING FOR THE HOLD-BASED FLOW
    return {                                                                                                             # BUILD RESPONSE
        "id": booking.id,                                                                                                # BOOKING ID (event-details.js REDIRECTS ON THIS)
        "user_id": booking.user_id,                                                                                      # OWNING USER
        "event_id": booking.event_id,                                                                                    # TARGET EVENT
        "tickets": booking.tickets,                                                                                      # LEGACY QUANTITY FIELD
        "status": booking.status,                                                                                        # NEW LIFECYCLE STATUS (pending/held/confirmed/...)
        "total_amount": booking.total_amount,                                                                            # SERVER-COMPUTED TOTAL
        "expires_at": booking.expires_at,                                                                                # HOLD EXPIRY
        "booking_time": booking.booking_time,                                                                            # CREATION TIME
        "payment_status": booking.payment_status,                                                                        # LEGACY PAYMENT STATUS FIELD
    }                                                                                                                     # END RESPONSE


@router.post("")                                                                                                         # CREATE + HOLD IN ONE CALL (matches event-details.js's POST /api/bookings exactly, no trailing slash)
@limiter.limit("10/minute")
def create_inventory_booking(request: Request, payload: InventoryBookingRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):  # UNIFIED HOLD ENTRY POINT
    db_user = get_authenticated_user(user, db)                                                                            # RESOLVE AUTHENTICATED USER

    if not (payload.seat_ids or payload.zone_id or payload.ticket_type_id):                                              # REQUIRE EXACTLY ONE INVENTORY SELECTION
        raise HTTPException(status_code=400, detail="Must specify seat_ids, zone_id, or ticket_type_id")                # REJECT AMBIGUOUS REQUEST

    booking_service = BookingService(db)                                                                                 # LIFECYCLE ORCHESTRATION
    inventory_service = InventoryService(db)                                                                             # SAFE, LOCKED HOLD OPERATIONS

    try:                                                                                                                 # START HOLD SEQUENCE
        booking = booking_service.create_hold(                                                                          # CREATE OR REUSE (VIA IDEMPOTENCY KEY) A PENDING BOOKING
            user_id=db_user.id,
            event_id=payload.event_id,
            idempotency_key=payload.idempotency_key,
        )

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


@router.post("/book")                                                                                                    # BOOK GENERAL OR ZONE INVENTORY
@limiter.limit("10/minute")
def book_event(request: Request, booking: schemas.BookingCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):  # CREATE NON-SEATED BOOKING
    if booking.tickets <= 0:                                                                                              # VALIDATE TICKET QUANTITY
        raise HTTPException(status_code=400, detail="Tickets must be greater than 0")                                   # REJECT INVALID QUANTITY
    db_user = get_authenticated_user(user, db)                                                                            # RESOLVE AUTHENTICATED USER
    try:                                                                                                                 # START ATOMIC BOOKING TRANSACTION
        event = db.query(models.Event).filter(models.Event.id == booking.event_id).with_for_update().first()           # LOCK EVENT INVENTORY ROW
        if not event:                                                                                                    # VALIDATE EVENT EXISTENCE
            raise HTTPException(status_code=404, detail="Event not found")                                              # RETURN EVENT NOT FOUND
        if event.inventory_type == models.INVENTORY_SEAT:                                                               # PREVENT BYPASSING SEAT SELECTION
            raise HTTPException(status_code=400, detail="This event requires seat selection")                           # REQUIRE FIXED-SEAT FLOW
        if event.available_seats < booking.tickets:                                                                      # VALIDATE AVAILABLE INVENTORY
            raise HTTPException(status_code=409, detail="Not enough seats available")                                   # RETURN INVENTORY CONFLICT
        event.available_seats -= booking.tickets                                                                         # ATOMICALLY RESERVE INVENTORY
        new_booking = models.Booking(user_id=db_user.id, event_id=event.id, tickets=booking.tickets, payment_status="pending")  # CREATE BOOKING RECORD
        db.add(new_booking)                                                                                                # ADD BOOKING TO TRANSACTION
        db.flush()                                                                                                        # GENERATE BOOKING ID
        ticket_price = event.price if event.price is not None else 0                                                   # DETERMINE CURRENT EVENT PRICE
        for _ in range(booking.tickets):                                                                                  # CREATE INDIVIDUAL TICKETS
            db.add(models.Ticket(booking_id=new_booking.id, event_id=event.id, ticket_code=generate_ticket_code(), qr_token=generate_qr_token(), price_paid=ticket_price, status="confirmed"))  # CREATE TICKET RECORD
        db.add(models.Notification(message=f"Booking created for event {event.id}", user_id=db_user.id))                # CREATE USER NOTIFICATION
        db.commit()                                                                                                      # COMMIT INVENTORY BOOKING AND TICKETS TOGETHER
        db.refresh(new_booking)                                                                                           # REFRESH BOOKING FROM DATABASE
        return new_booking                                                                                                # RETURN CREATED BOOKING
    except HTTPException:                                                                                                # HANDLE EXPECTED BUSINESS ERRORS
        db.rollback()                                                                                                    # ROLLBACK TRANSACTION
        raise                                                                                                           # PRESERVE ORIGINAL ERROR
    except Exception:                                                                                                    # HANDLE UNEXPECTED DATABASE ERRORS
        db.rollback()                                                                                                    # ROLLBACK FAILED TRANSACTION
        raise HTTPException(status_code=500, detail="Unable to create booking")                                         # RETURN SAFE SERVER ERROR


@router.post("/book/seats")                                                                                              # CREATE FIXED-SEAT BOOKING FROM ACTIVE LOCK
@limiter.limit("10/minute")
def book_seats(request: Request, data: schemas_seating.ConfirmSeatBookingRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):  # CONVERT SEAT LOCKS INTO BOOKING
    db_user = get_authenticated_user(user, db)                                                                            # RESOLVE AUTHENTICATED USER
    now = datetime.now(timezone.utc)                                                                                      # GET CURRENT UTC TIME
    try:                                                                                                                 # START ATOMIC SEAT BOOKING TRANSACTION
        locks = db.query(models.SeatLock).filter(models.SeatLock.lock_token == data.lock_token, models.SeatLock.user_id == db_user.id, models.SeatLock.status == models.LOCK_ACTIVE).with_for_update().all()  # LOCK USER'S ACTIVE SEAT HOLDS
        if not locks:                                                                                                    # VALIDATE ACTIVE LOCK
            raise HTTPException(status_code=404, detail="Active seat lock not found")                                   # RETURN LOCK NOT FOUND
        if any(lock.expires_at <= now for lock in locks):                                                               # CHECK LOCK EXPIRATION
            for lock in locks:                                                                                           # RELEASE EXPIRED LOCKS
                lock.status = models.LOCK_EXPIRED                                                                         # MARK LOCK EXPIRED
                lock.released_at = now if hasattr(lock, "released_at") else None                                       # PRESERVE COMPATIBILITY WITH CURRENT MODEL
                lock.seat.status = models.SEAT_AVAILABLE                                                                 # RETURN SEAT TO INVENTORY
            db.flush()                                                                                                   # APPLY EXPIRATION BEFORE ROLLBACK/ERROR
            raise HTTPException(status_code=409, detail="Seat lock has expired")                                        # REQUIRE SEAT RESELECTION
        event_ids = {lock.seat.event_id for lock in locks}                                                              # COLLECT EVENT IDS FROM LOCKED SEATS
        if len(event_ids) != 1:                                                                                          # PREVENT CROSS-EVENT BOOKING
            raise HTTPException(status_code=400, detail="Seat lock contains seats from multiple events")               # REJECT INVALID LOCK
        event_id = next(iter(event_ids))                                                                                 # GET TARGET EVENT ID
        event = db.query(models.Event).filter(models.Event.id == event_id).with_for_update().first()                   # LOCK EVENT INVENTORY ROW
        if not event:                                                                                                    # VALIDATE EVENT EXISTENCE
            raise HTTPException(status_code=404, detail="Event not found")                                              # RETURN EVENT NOT FOUND
        if event.inventory_type != models.INVENTORY_SEAT:                                                              # VALIDATE FIXED-SEAT EVENT
            raise HTTPException(status_code=400, detail="Event does not use fixed seating")                             # REJECT INVALID INVENTORY
        seats = [lock.seat for lock in locks]                                                                            # RESOLVE LOCKED SEATS
        if any(seat.status != models.SEAT_LOCKED for seat in seats):                                                   # VALIDATE INVENTORY STATE
            raise HTTPException(status_code=409, detail="One or more seats are no longer available")                   # PREVENT INVALID CONVERSION
        new_booking = models.Booking(user_id=db_user.id, event_id=event.id, tickets=len(seats), payment_status="pending")  # CREATE SEATED BOOKING
        db.add(new_booking)                                                                                              # ADD BOOKING TO TRANSACTION
        db.flush()                                                                                                      # GENERATE BOOKING ID
        for lock in locks:                                                                                              # CONVERT EACH LOCKED SEAT
            seat = lock.seat                                                                                             # RESOLVE LOCKED SEAT
            seat.status = models.SEAT_SOLD                                                                                 # MOVE SEAT TO SOLD STATE
            lock.status = models.LOCK_CONVERTED                                                                           # CONVERT TEMPORARY LOCK
            ticket_price = seat.price if seat.price is not None else event.price or 0                                  # CAPTURE PRICE AT BOOKING TIME
            db.add(models.Ticket(booking_id=new_booking.id, event_id=event.id, seat_id=seat.id, zone_id=seat.zone_id, ticket_code=generate_ticket_code(), qr_token=generate_qr_token(), price_paid=ticket_price, status="confirmed"))  # CREATE SEAT TICKET
            zone = seat.zone                                                                                             # RESOLVE SEAT ZONE
            if zone:                                                                                                     # UPDATE ZONE COUNTERS
                zone.locked_count = max(0, zone.locked_count - 1)                                                        # REMOVE ACTIVE LOCK COUNT
                zone.sold_count += 1                                                                                     # INCREMENT SOLD COUNT
        event.available_seats = max(0, event.available_seats - len(seats))                                             # DECREASE EVENT INVENTORY
        db.add(models.Notification(message=f"Booking created for event {event.id}", user_id=db_user.id))              # CREATE USER NOTIFICATION
        db.commit()                                                                                                     # ATOMICALLY COMMIT BOOKING AND SEAT CONVERSION
        db.refresh(new_booking)                                                                                          # REFRESH BOOKING
        return {"success": True, "booking_id": new_booking.id, "event_id": event.id, "tickets": len(seats), "status": new_booking.payment_status, "lock_token": data.lock_token}  # RETURN BOOKING RESULT
    except HTTPException:                                                                                                # HANDLE EXPECTED BUSINESS ERRORS
        db.rollback()                                                                                                    # ROLLBACK TRANSACTION
        raise                                                                                                           # PRESERVE ORIGINAL ERROR
    except Exception:                                                                                                    # HANDLE UNEXPECTED DATABASE ERRORS
        db.rollback()                                                                                                    # ROLLBACK FAILED TRANSACTION
        raise HTTPException(status_code=500, detail="Unable to create seat booking")                                    # RETURN SAFE SERVER ERROR


@router.get("/my-bookings")                                                                                              # GET CURRENT USER BOOKINGS
def my_bookings(user=Depends(get_current_user), db: Session = Depends(get_db)):                                        # RETURN USER BOOKING HISTORY
    db_user = get_authenticated_user(user, db)                                                                            # RESOLVE AUTHENTICATED USER
    bookings = db.query(models.Booking).filter(models.Booking.user_id == db_user.id).order_by(models.Booking.booking_time.desc()).all()  # GET BOOKINGS IN NEWEST-FIRST ORDER
    result = []                                                                                                         # BUILD FRONTEND RESPONSE
    for booking in bookings:                                                                                             # PROCESS EACH BOOKING
        tickets = [{"id": ticket.id, "ticket_code": ticket.ticket_code, "seat_id": ticket.seat_id, "zone_id": ticket.zone_id, "price_paid": ticket.price_paid, "status": ticket.status} for ticket in booking.tickets_rel]  # SERIALIZE BOOKING TICKETS
        result.append({"id": booking.id, "tickets": booking.tickets, "status": booking.payment_status, "booking_time": booking.booking_time, "ticket_details": tickets, "event": {"title": booking.event.title if booking.event else "N/A", "date_time": booking.event.date_time if booking.event else "", "location": booking.event.location if booking.event else "", "image_url": booking.event.image_url if booking.event else "", "category": booking.event.category if booking.event else ""}})  # BUILD BOOKING RESPONSE
    return result                                                                                                      # RETURN BOOKING HISTORY


@router.delete("/book/{booking_id}")                                                                                    # CANCEL BOOKING
def cancel_booking(booking_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):                   # CANCEL CURRENT USER BOOKING
    db_user = get_authenticated_user(user, db)                                                                            # RESOLVE AUTHENTICATED USER
    try:                                                                                                                 # START ATOMIC CANCELLATION TRANSACTION
        booking = db.query(models.Booking).filter(models.Booking.id == booking_id, models.Booking.user_id == db_user.id).with_for_update().first()  # LOCK USER BOOKING
        if not booking:                                                                                                 # VALIDATE BOOKING EXISTENCE
            raise HTTPException(status_code=404, detail="Booking not found")                                           # RETURN BOOKING NOT FOUND
        if booking.payment_status == "cancelled":                                                                        # PREVENT DUPLICATE CANCELLATION
            raise HTTPException(status_code=409, detail="Booking is already cancelled")                                # RETURN CURRENT STATE ERROR
        event = db.query(models.Event).filter(models.Event.id == booking.event_id).with_for_update().first()          # LOCK EVENT INVENTORY
        if not event:                                                                                                   # VALIDATE EVENT EXISTENCE
            raise HTTPException(status_code=404, detail="Event not found")                                              # RETURN EVENT NOT FOUND
        active_tickets = [ticket for ticket in booking.tickets_rel if ticket.status != "cancelled"]                  # SELECT TICKETS THAT CAN BE CANCELLED
        if not active_tickets:                                                                                          # VALIDATE ACTIVE TICKETS
            raise HTTPException(status_code=409, detail="Booking has no active tickets")                              # RETURN INVALID STATE
        for ticket in active_tickets:                                                                                   # RELEASE BOOKED INVENTORY
            if ticket.seat_id:                                                                                          # HANDLE FIXED SEAT TICKET
                seat = db.query(models.Seat).filter(models.Seat.id == ticket.seat_id).with_for_update().first()       # LOCK SOLD SEAT
                if seat and seat.status == models.SEAT_SOLD:                                                          # VALIDATE SOLD STATE
                    seat.status = models.SEAT_AVAILABLE                                                               # RETURN SEAT TO INVENTORY
                    if seat.zone:                                                                                       # UPDATE ZONE COUNTERS
                        seat.zone.sold_count = max(0, seat.zone.sold_count - 1)                                        # DECREMENT SOLD COUNT
                ticket.status = "cancelled"                                                                             # CANCEL SEAT TICKET
            else:                                                                                                      # HANDLE GENERAL/ZONE TICKET
                ticket.status = "cancelled"                                                                             # CANCEL NON-SEATED TICKET
        event.available_seats += len(active_tickets)                                                                     # RESTORE EVENT INVENTORY
        booking.payment_status = "cancelled"                                                                            # RETAIN BOOKING HISTORY WITH CANCELLED STATE
        db.add(models.Notification(message=f"Booking cancelled for event {event.id}", user_id=db_user.id))            # CREATE CANCELLATION NOTIFICATION
        db.commit()                                                                                                     # ATOMICALLY COMMIT CANCELLATION
        return {"success": True, "message": "Booking cancelled successfully", "booking_id": booking.id}                # RETURN CANCELLATION RESULT
    except HTTPException:                                                                                                # HANDLE EXPECTED BUSINESS ERRORS
        db.rollback()                                                                                                    # ROLLBACK TRANSACTION
        raise                                                                                                           # PRESERVE ORIGINAL ERROR
    except Exception:                                                                                                    # HANDLE UNEXPECTED DATABASE ERRORS
        db.rollback()                                                                                                    # ROLLBACK FAILED TRANSACTION
        raise HTTPException(status_code=500, detail="Unable to cancel booking")                                        # RETURN SAFE SERVER ERROR