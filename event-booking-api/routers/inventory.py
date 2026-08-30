from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from utils.helpers import get_db
from services.inventory_service import InventoryService
from core.security import get_current_user
import models


router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


class SeatHoldRequest(BaseModel):
    event_id: int = Field(..., gt=0)
    seat_ids: list[int] = Field(..., min_length=1)
    booking_id: int = Field(..., gt=0)


class ZoneHoldRequest(BaseModel):
    event_id: int = Field(..., gt=0)
    zone_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    booking_id: int = Field(..., gt=0)


class PassHoldRequest(BaseModel):
    event_id: int = Field(..., gt=0)
    ticket_type_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    booking_id: int = Field(..., gt=0)


class BookingInventoryRequest(BaseModel):
    booking_id: int = Field(..., gt=0)


def get_authenticated_user(user, db: Session) -> models.User:                                        # RESOLVE REAL DB USER FROM JWT PAYLOAD (dict, not ORM object)
    db_user = db.query(models.User).filter(models.User.username == user["username"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if not db_user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")
    return db_user


def _booking_response(booking: models.Booking) -> dict:
    return {
        "id": booking.id,
        "user_id": booking.user_id,
        "event_id": booking.event_id,
        "tickets": booking.tickets,
        "status": booking.status,
        "total_amount": booking.total_amount,
        "expires_at": booking.expires_at,
        "booking_time": booking.booking_time,
        "payment_status": booking.payment_status,
    }


@router.get("/event/{event_id}")
def get_event_inventory(
    event_id: int,
    db: Session = Depends(get_db),
):
    service = InventoryService(db)

    try:
        inventory = service.get_event_inventory(event_id)

        return {
            "event_id": event_id,
            "inventory": [
                {
                    "id": item.id,
                    "event_id": item.event_id,
                    "inventory_type": item.inventory_type,
                    "status": item.status,
                    "price": item.price,
                    "seat_id": item.seat_id,
                    "zone_id": item.zone_id,
                    "ticket_type_id": item.ticket_type_id,
                    "locked_until": item.locked_until,
                }
                for item in inventory
            ],
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/hold/seats")
def hold_seats(
    request: SeatHoldRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = get_authenticated_user(user, db)
    service = InventoryService(db)

    try:
        booking = service.hold_seats(
            event_id=request.event_id,
            seat_ids=request.seat_ids,
            user_id=db_user.id,
            booking_id=request.booking_id,
        )

        return {
            "message": "Seats held successfully",
            "booking": _booking_response(booking),
        }

    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/hold/zone")
def hold_zone(
    request: ZoneHoldRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = get_authenticated_user(user, db)
    service = InventoryService(db)

    try:
        booking = service.hold_zone(
            event_id=request.event_id,
            zone_id=request.zone_id,
            quantity=request.quantity,
            user_id=db_user.id,
            booking_id=request.booking_id,
        )

        return {
            "message": "Zone inventory held successfully",
            "booking": _booking_response(booking),
        }

    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/hold/passes")
def hold_passes(
    request: PassHoldRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = get_authenticated_user(user, db)
    service = InventoryService(db)

    try:
        booking = service.hold_passes(
            event_id=request.event_id,
            ticket_type_id=request.ticket_type_id,
            quantity=request.quantity,
            user_id=db_user.id,
            booking_id=request.booking_id,
        )

        return {
            "message": "Pass inventory held successfully",
            "booking": _booking_response(booking),
        }

    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/release/seats")
def release_seats(
    request: BookingInventoryRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = get_authenticated_user(user, db)
    service = InventoryService(db)

    try:
        released = service.release_seats(
            booking_id=request.booking_id,
            user_id=db_user.id,
        )

        return {
            "message": "Seats released successfully",
            "booking_id": request.booking_id,
            "released_quantity": released,
        }

    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/release/zone")
def release_zone(
    request: BookingInventoryRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = get_authenticated_user(user, db)
    service = InventoryService(db)

    try:
        released = service.release_zone(
            booking_id=request.booking_id,
            user_id=db_user.id,
        )

        return {
            "message": "Zone inventory released successfully",
            "booking_id": request.booking_id,
            "released_quantity": released,
        }

    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/release/passes")
def release_passes(
    request: BookingInventoryRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = get_authenticated_user(user, db)
    service = InventoryService(db)

    try:
        released = service.release_passes(
            booking_id=request.booking_id,
            user_id=db_user.id,
        )

        return {
            "message": "Pass inventory released successfully",
            "booking_id": request.booking_id,
            "released_quantity": released,
        }

    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/confirm")
def confirm_inventory(
    request: BookingInventoryRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = get_authenticated_user(user, db)
    service = InventoryService(db)

    try:
        booking = service.confirm_inventory(
            booking_id=request.booking_id,
            user_id=db_user.id,
        )

        return {
            "message": "Inventory confirmed successfully",
            "booking": _booking_response(booking),
        }

    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/release-expired")
def release_expired_holds(
    batch_size: int = 100,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if batch_size <= 0 or batch_size > 1000:
        raise HTTPException(
            status_code=400,
            detail="batch_size must be between 1 and 1000",
        )

    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    service = InventoryService(db)

    try:
        released_count = service.release_expired_holds(
            batch_size=batch_size,
        )

        return {
            "message": "Expired inventory holds processed successfully",
            "released_bookings": released_count,
        }

    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))