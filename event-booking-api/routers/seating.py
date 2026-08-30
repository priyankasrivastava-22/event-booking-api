from datetime import datetime, timedelta, timezone                                      # DATE AND TIME UTILITIES
import secrets                                                                             # SECURE RANDOM TOKEN GENERATION
import uuid                                                                                # UNIQUE TICKET IDENTIFIER GENERATION

from fastapi import APIRouter, Depends, HTTPException, status                             # FASTAPI ROUTING AND DEPENDENCY INJECTION
from sqlalchemy.orm import Session                                                         # SQLALCHEMY DATABASE SESSION

import models                                                                              # DATABASE MODELS
import schemas_seating                                                                      # SEATING PYDANTIC SCHEMAS

from utils.helpers import get_db                                                           # DATABASE SESSION DEPENDENCY
from core.security import get_current_user                                                 # AUTHENTICATED USER DEPENDENCY


router = APIRouter()                                                                        # SEATING ROUTER


LOCK_DURATION_MINUTES = 10                                                                  # TEMPORARY SEAT LOCK DURATION


def require_admin(user: models.User):                                                                                   # ADMIN AUTHORIZATION
    if user.role != "admin":                                                                # ALLOW ONLY ADMIN USERS
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")  # DENY NON-ADMIN ACCESS


@router.post("/admin/events/{event_id}/layout")                                                                         # CREATE EVENT LAYOUT
def create_layout(event_id: int, data: schemas_seating.LayoutCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):  # CREATE LAYOUT WITH AUTHENTICATED ADMIN
    require_admin(current_user)                                                             # VERIFY ADMIN ROLE

    event = db.query(models.Event).filter(models.Event.id == event_id).first()              # FIND TARGET EVENT

    if not event:                                                                            # VALIDATE EVENT EXISTENCE
        raise HTTPException(status_code=404, detail="Event not found")                      # RETURN NOT FOUND

    existing = db.query(models.VenueLayout).filter(models.VenueLayout.event_id == event_id).first()  # CHECK EXISTING EVENT LAYOUT

    if existing:                                                                             # PREVENT MULTIPLE PRIMARY LAYOUTS
        raise HTTPException(status_code=409, detail="Event already has a venue layout")      # RETURN CONFLICT

    layout = models.VenueLayout(event_id=event_id, name=data.name)                           # CREATE VENUE LAYOUT

    db.add(layout)                                                                            # ADD LAYOUT TO TRANSACTION
    db.commit()                                                                               # COMMIT LAYOUT
    db.refresh(layout)                                                                        # REFRESH GENERATED DATABASE FIELDS

    return layout                                                                             # RETURN CREATED LAYOUT


@router.post("/admin/layouts/{layout_id}/zones")                                                                        # CREATE ZONE
def create_zone(layout_id: int, data: schemas_seating.ZoneCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):  # CREATE ZONE WITH AUTHENTICATED ADMIN
    require_admin(current_user)                                                             # VERIFY ADMIN ROLE

    layout = db.query(models.VenueLayout).filter(models.VenueLayout.id == layout_id).first()  # FIND TARGET LAYOUT

    if not layout:                                                                           # VALIDATE LAYOUT EXISTENCE
        raise HTTPException(status_code=404, detail="Layout not found")                     # RETURN NOT FOUND

    existing = db.query(models.EventZone).filter(models.EventZone.layout_id == layout_id, models.EventZone.code == data.code).first()  # CHECK DUPLICATE ZONE CODE

    if existing:                                                                             # PREVENT DUPLICATE ZONE CODE
        raise HTTPException(status_code=409, detail="Zone code already exists")              # RETURN CONFLICT

    zone = models.EventZone(event_id=layout.event_id, layout_id=layout_id, name=data.name, code=data.code, zone_type=data.zone_type, capacity=data.capacity, base_price=data.base_price)  # CREATE EVENT ZONE

    db.add(zone)                                                                             # ADD ZONE TO TRANSACTION
    db.commit()                                                                              # COMMIT ZONE
    db.refresh(zone)                                                                         # REFRESH GENERATED DATABASE FIELDS

    return zone                                                                              # RETURN CREATED ZONE


@router.post("/admin/zones/{zone_id}/rows")                                                                             # GENERATE ROW + SEATS
def create_row(zone_id: int, data: schemas_seating.RowCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):  # CREATE ROW WITH AUTHENTICATED ADMIN
    require_admin(current_user)                                                             # VERIFY ADMIN ROLE

    zone = db.query(models.EventZone).filter(models.EventZone.id == zone_id).first()        # FIND TARGET ZONE

    if not zone:                                                                             # VALIDATE ZONE EXISTENCE
        raise HTTPException(status_code=404, detail="Zone not found")                       # RETURN NOT FOUND

    if zone.zone_type != "seated":                                                           # ONLY SEATED ZONES CAN HAVE ROWS
        raise HTTPException(status_code=400, detail="Rows can only be created for seated zones")  # REJECT INVALID ZONE TYPE

    if data.seat_count > zone.capacity and zone.capacity > 0:                               # PREVENT ROW FROM EXCEEDING ZONE CAPACITY
        raise HTTPException(status_code=400, detail="Seat count exceeds zone capacity")      # RETURN CAPACITY ERROR

    existing_row = db.query(models.SeatRow).filter(models.SeatRow.zone_id == zone_id, models.SeatRow.row_label == data.row_label).first()  # CHECK DUPLICATE ROW

    if existing_row:                                                                          # PREVENT DUPLICATE ROW LABEL
        raise HTTPException(status_code=409, detail="Row already exists")                    # RETURN CONFLICT

    row = models.SeatRow(event_id=zone.event_id, zone_id=zone.id, row_label=data.row_label) # CREATE SEAT ROW

    try:                                                                                     # START ATOMIC ROW AND SEAT CREATION
        db.add(row)                                                                           # ADD ROW TO TRANSACTION
        db.flush()                                                                            # GENERATE ROW ID BEFORE CREATING SEATS

        seats = []                                                                            # STORE GENERATED SEATS

        for number in range(1, data.seat_count + 1):                                         # GENERATE SEAT NUMBERS
            seat_code = f"{zone.code}-{data.row_label}-{number}"                             # CREATE UNIQUE HUMAN-READABLE SEAT CODE
            seat = models.Seat(event_id=zone.event_id, zone_id=zone.id, row_id=row.id, seat_number=number, seat_code=seat_code, status=models.SEAT_AVAILABLE, price=data.starting_price or zone.base_price)  # CREATE AVAILABLE SEAT
            seats.append(seat)                                                               # ADD SEAT TO BATCH

        db.add_all(seats)                                                                    # ADD ALL GENERATED SEATS
        db.commit()                                                                          # COMMIT ROW AND ALL SEATS ATOMICALLY

    except Exception:                                                                        # HANDLE DATABASE CREATION FAILURE
        db.rollback()                                                                        # ROLLBACK PARTIAL CHANGES
        raise                                                                                # PROPAGATE ORIGINAL ERROR

    return {"success": True, "row_id": row.id, "row_label": row.row_label, "seats_created": len(seats)}  # RETURN GENERATION RESULT


@router.get("/events/{event_id}/seats", response_model=list[schemas_seating.SeatResponse])                              # PUBLIC SEAT MAP
def get_event_seats(event_id: int, db: Session = Depends(get_db)):                           # FETCH EVENT SEATS

    event = db.query(models.Event).filter(models.Event.id == event_id).first()               # FIND TARGET EVENT

    if not event:                                                                            # VALIDATE EVENT EXISTENCE
        raise HTTPException(status_code=404, detail="Event not found")                       # RETURN NOT FOUND

    if event.inventory_type != models.INVENTORY_SEAT:                                       # VALIDATE FIXED-SEAT INVENTORY
        raise HTTPException(status_code=400, detail="Event does not use fixed seating")     # REJECT NON-SEATED INVENTORY

    seats = db.query(models.Seat).filter(models.Seat.event_id == event_id).order_by(models.Seat.zone_id, models.Seat.row_id, models.Seat.seat_number).all()  # FETCH SEATS IN VENUE ORDER

    return seats                                                                              # RETURN SEAT MAP


@router.post("/events/{event_id}/seats/lock", response_model=schemas_seating.SeatHoldResponse)                          # LOCK SEATS
def lock_seats(event_id: int, data: schemas_seating.SeatHoldRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):  # LOCK SEATS FOR AUTHENTICATED USER

    if len(set(data.seat_ids)) != len(data.seat_ids):                                        # DETECT DUPLICATE SEAT IDS
        raise HTTPException(status_code=400, detail="Duplicate seat IDs are not allowed")   # REJECT DUPLICATE REQUEST

    event = db.query(models.Event).filter(models.Event.id == event_id).first()               # FIND TARGET EVENT

    if not event:                                                                            # VALIDATE EVENT EXISTENCE
        raise HTTPException(status_code=404, detail="Event not found")                       # RETURN NOT FOUND

    if event.inventory_type != models.INVENTORY_SEAT:                                       # VALIDATE FIXED-SEAT INVENTORY
        raise HTTPException(status_code=400, detail="Event does not use fixed seating")     # REJECT INVALID INVENTORY TYPE

    now = datetime.now(timezone.utc)                                                         # GET CURRENT UTC TIME

    try:                                                                                     # START ATOMIC SEAT-LOCK TRANSACTION

        seats = db.query(models.Seat).filter(models.Seat.event_id == event_id, models.Seat.id.in_(data.seat_ids)).with_for_update().all()  # LOCK DATABASE ROWS TO PREVENT COLLISION

        if len(seats) != len(data.seat_ids):                                                 # VALIDATE THAT EVERY REQUESTED SEAT BELONGS TO EVENT
            db.rollback()                                                                    # ROLLBACK TRANSACTION
            raise HTTPException(status_code=404, detail="One or more seats not found")      # RETURN INVALID SEAT ERROR

        expired_locks = db.query(models.SeatLock).filter(models.SeatLock.seat_id.in_(data.seat_ids), models.SeatLock.status == models.LOCK_ACTIVE, models.SeatLock.expires_at <= now).with_for_update().all()  # FIND AND LOCK EXPIRED HOLDS

        for lock in expired_locks:                                                           # RELEASE EACH EXPIRED LOCK
            lock.status = models.LOCK_EXPIRED                                               # MARK LOCK EXPIRED
            lock.released_at = now                                                           # RECORD LOCK RELEASE TIME
            lock.seat.status = models.SEAT_AVAILABLE                                         # RETURN SEAT TO AVAILABLE STATE

        db.flush()                                                                           # APPLY EXPIRED LOCK STATE BEFORE VALIDATION

        for seat in seats:                                                                    # VALIDATE EVERY REQUESTED SEAT

            if seat.status == models.SEAT_SOLD:                                              # PREVENT SOLD SEAT REUSE
                db.rollback()                                                                # ROLLBACK TRANSACTION
                raise HTTPException(status_code=409, detail=f"Seat {seat.seat_code} is already sold")  # RETURN SOLD CONFLICT

            if seat.status == models.SEAT_LOCKED:                                            # CHECK CURRENTLY LOCKED SEAT

                active_lock = db.query(models.SeatLock).filter(models.SeatLock.seat_id == seat.id, models.SeatLock.status == models.LOCK_ACTIVE, models.SeatLock.expires_at > now).with_for_update().first()  # FETCH ACTIVE LOCK

                if active_lock and active_lock.user_id != current_user.id:                   # PREVENT ANOTHER USER FROM TAKING LOCKED SEAT
                    db.rollback()                                                            # ROLLBACK TRANSACTION
                    raise HTTPException(status_code=409, detail=f"Seat {seat.seat_code} is currently locked")  # RETURN LOCK CONFLICT

                if active_lock and active_lock.user_id == current_user.id:                  # PREVENT DUPLICATE ACTIVE LOCK FOR SAME USER
                    db.rollback()                                                            # ROLLBACK TRANSACTION
                    raise HTTPException(status_code=409, detail=f"Seat {seat.seat_code} is already locked by you")  # RETURN DUPLICATE LOCK ERROR

        lock_token = secrets.token_urlsafe(48)                                                # GENERATE SECURE NON-GUESSABLE LOCK TOKEN
        expires_at = now + timedelta(minutes=LOCK_DURATION_MINUTES)                          # CALCULATE LOCK EXPIRATION TIME

        for seat in seats:                                                                    # CREATE LOCK FOR EACH SELECTED SEAT
            seat.status = models.SEAT_LOCKED                                               # CHANGE SEAT INVENTORY STATE TO LOCKED
            db.add(models.SeatLock(seat_id=seat.id, user_id=current_user.id, lock_token=lock_token, status=models.LOCK_ACTIVE, locked_at=now, expires_at=expires_at))  # CREATE USER-OWNED TEMPORARY LOCK

        db.commit()                                                                          # ATOMICALLY COMMIT ALL SEAT LOCKS

    except HTTPException:                                                                     # HANDLE EXPECTED BUSINESS ERRORS
        raise                                                                                 # PRESERVE HTTP ERROR

    except Exception:                                                                         # HANDLE UNEXPECTED DATABASE ERRORS
        db.rollback()                                                                         # ROLLBACK TRANSACTION
        raise HTTPException(status_code=500, detail="Unable to lock seats")                  # RETURN SAFE GENERIC ERROR

    return {"lock_token": lock_token, "expires_at": expires_at.isoformat(), "seats": [seat.id for seat in seats]}  # RETURN LOCK DETAILS


@router.post("/events/{event_id}/seats/confirm")                                             # CONFIRM SEAT BOOKING
def confirm_seat_booking(event_id: int, data: schemas_seating.ConfirmSeatBookingRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):  # CONFIRM LOCK AND CREATE BOOKING

    now = datetime.now(timezone.utc)                                                         # GET CURRENT UTC TIME

    try:                                                                                     # START ATOMIC BOOKING TRANSACTION

        event = db.query(models.Event).filter(models.Event.id == event_id).with_for_update().first()  # LOCK EVENT ROW FOR CONSISTENT INVENTORY UPDATE

        if not event:                                                                        # VALIDATE EVENT EXISTENCE
            raise HTTPException(status_code=404, detail="Event not found")                  # RETURN NOT FOUND

        if event.inventory_type != models.INVENTORY_SEAT:                                   # VALIDATE FIXED-SEAT INVENTORY
            raise HTTPException(status_code=400, detail="Event does not use fixed seating") # REJECT INVALID INVENTORY TYPE

        locks = db.query(models.SeatLock).filter(models.SeatLock.lock_token == data.lock_token, models.SeatLock.user_id == current_user.id, models.SeatLock.status == models.LOCK_ACTIVE).with_for_update().all()  # FETCH ONLY ACTIVE USER-OWNED LOCKS

        if not locks:                                                                        # VALIDATE LOCK EXISTENCE
            raise HTTPException(status_code=404, detail="Active seat lock not found")        # RETURN LOCK NOT FOUND

        if any(lock.seat.event_id != event_id for lock in locks):                            # PREVENT CROSS-EVENT LOCK TOKEN REUSE
            raise HTTPException(status_code=400, detail="Seat lock does not belong to this event")  # REJECT INVALID EVENT CONTEXT

        if any(lock.expires_at <= now for lock in locks):                                    # CHECK LOCK EXPIRATION
            for lock in locks:                                                               # RELEASE EXPIRED LOCKS
                lock.status = models.LOCK_EXPIRED                                            # MARK LOCK EXPIRED
                lock.released_at = now                                                       # RECORD RELEASE TIME
                lock.seat.status = models.SEAT_AVAILABLE                                    # RETURN SEAT TO INVENTORY

            db.commit()                                                                      # SAVE EXPIRED LOCK STATE
            raise HTTPException(status_code=409, detail="Seat lock has expired")            # REQUIRE NEW SEAT SELECTION

        seat_ids = [lock.seat_id for lock in locks]                                          # COLLECT LOCKED SEAT IDS

        seats = db.query(models.Seat).filter(models.Seat.id.in_(seat_ids), models.Seat.event_id == event_id).with_for_update().all()  # LOCK SEATS BEFORE FINAL BOOKING

        if len(seats) != len(seat_ids):                                                      # VERIFY ALL LOCKED SEATS STILL EXIST
            raise HTTPException(status_code=409, detail="One or more seats are no longer available")  # RETURN INVENTORY CONFLICT

        if any(seat.status != models.SEAT_LOCKED for seat in seats):                        # PREVENT BOOKING NON-LOCKED SEATS
            raise HTTPException(status_code=409, detail="One or more seats are no longer locked")  # RETURN STATE CONFLICT

        total_amount = sum(seat.price for seat in seats)                                    # CALCULATE TOTAL PRICE FROM SERVER-SIDE SEAT PRICES

        booking = models.Booking(user_id=current_user.id, event_id=event_id, tickets=len(seats), total_amount=total_amount)  # CREATE BOOKING USING IMMUTABLE USER ID

        db.add(booking)                                                                       # ADD BOOKING TO TRANSACTION
        db.flush()                                                                            # GENERATE BOOKING ID BEFORE CREATING TICKETS

        created_tickets = []                                                                  # STORE GENERATED TICKETS

        for seat in seats:                                                                    # CREATE ONE TICKET PER CONFIRMED SEAT

            ticket = models.Ticket(                                                          # CREATE SEAT-LINKED TICKET
                booking_id=booking.id,                                                       # LINK TICKET TO BOOKING
                user_id=current_user.id,                                                     # LINK TICKET TO AUTHENTICATED USER
                event_id=event_id,                                                           # LINK TICKET TO EVENT
                seat_id=seat.id,                                                             # LINK TICKET TO EXACT SEAT
                ticket_code=uuid.uuid4().hex,                                                # GENERATE UNIQUE TICKET CODE
                price=seat.price                                                             # STORE PRICE USED FOR THIS TICKET
            )

            created_tickets.append(ticket)                                                   # STORE GENERATED TICKET

            seat.status = models.SEAT_SOLD                                                     # PERMANENTLY MARK SEAT AS SOLD

        db.add_all(created_tickets)                                                          # ADD ALL TICKETS TO TRANSACTION

        for lock in locks:                                                                    # CONVERT ACTIVE LOCKS AFTER SUCCESSFUL BOOKING
            lock.status = models.LOCK_CONVERTED                                               # MARK LOCK AS CONVERTED
            lock.released_at = now                                                           # RECORD LOCK CONVERSION TIME

        if hasattr(event, "available_seats") and event.available_seats is not None:          # UPDATE LEGACY EVENT-LEVEL INVENTORY COUNTER
            event.available_seats = max(0, event.available_seats - len(seats))              # DECREMENT AVAILABLE SEAT COUNT SAFELY

        db.commit()                                                                          # ATOMICALLY COMMIT BOOKING TICKETS SEATS AND LOCK CONVERSION
        db.refresh(booking)                                                                  # REFRESH CREATED BOOKING

        return {                                                                             # RETURN CONFIRMED BOOKING
            "success": True,                                                                 # CONFIRM SUCCESS
            "booking_id": booking.id,                                                        # RETURN BOOKING IDENTIFIER
            "event_id": event_id,                                                            # RETURN EVENT IDENTIFIER
            "user_id": current_user.id,                                                      # RETURN AUTHENTICATED USER IDENTIFIER
            "tickets": [                                                                      # RETURN GENERATED TICKETS
                {                                                                             # TICKET RESPONSE OBJECT
                    "ticket_id": ticket.id,                                                  # RETURN TICKET ID
                    "ticket_code": ticket.ticket_code,                                       # RETURN UNIQUE TICKET CODE
                    "seat_id": ticket.seat_id,                                               # RETURN SEAT ID
                    "price": ticket.price                                                     # RETURN SERVER-CALCULATED PRICE
                } for ticket in created_tickets                                               # BUILD RESPONSE FOR EACH TICKET
            ],                                                                                # END TICKET RESPONSE
            "total_amount": total_amount                                                      # RETURN SERVER-CALCULATED TOTAL
        }                                                                                     # END BOOKING RESPONSE

    except HTTPException:                                                                     # HANDLE EXPECTED BUSINESS ERRORS
        db.rollback()                                                                        # ROLLBACK CURRENT TRANSACTION
        raise                                                                                # PRESERVE HTTP ERROR

    except Exception:                                                                         # HANDLE UNEXPECTED DATABASE ERRORS
        db.rollback()                                                                         # ROLLBACK EVERYTHING TO PREVENT PARTIAL BOOKING
        raise HTTPException(status_code=500, detail="Unable to confirm seat booking")         # RETURN SAFE GENERIC ERROR