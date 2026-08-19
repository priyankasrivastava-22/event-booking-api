from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
import schemas

from core.security import get_db, get_current_user
from utils.helpers import generate_transaction_id

router = APIRouter()

# ---------------- CREATE PAYMENT ----------------
@router.post("/", response_model=schemas.PaymentResponse)
def create_payment(
    data: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # --------------------------------------------------------
    # Resolve authenticated database user
    # --------------------------------------------------------
    db_user = db.query(models.User).filter(
        models.User.username == user["username"]
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # --------------------------------------------------------
    # Find booking belonging to authenticated user
    # --------------------------------------------------------
    booking = db.query(models.Booking).filter(
        models.Booking.id == data.booking_id,
        models.Booking.user_id == db_user.id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    # --------------------------------------------------------
    # Prevent duplicate successful payments
    # --------------------------------------------------------
    existing_payment = db.query(models.Payment).filter(
        models.Payment.booking_id == booking.id,
        models.Payment.status == "success"
    ).first()

    if existing_payment:
        raise HTTPException(
            status_code=400,
            detail="Payment already completed for this booking"
        )

    # --------------------------------------------------------
    # Do not allow payment for already cancelled booking
    # --------------------------------------------------------
    if booking.payment_status == "cancelled":
        raise HTTPException(
            status_code=400,
            detail="Cannot pay for a cancelled booking"
        )

    # --------------------------------------------------------
    # Find event
    # --------------------------------------------------------
    event = db.query(models.Event).filter(
        models.Event.id == booking.event_id
    ).first()

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Event not found"
        )

    # --------------------------------------------------------
    # Calculate amount
    # --------------------------------------------------------
    amount = booking.tickets * event.price

    # --------------------------------------------------------
    # Generate transaction ID
    # --------------------------------------------------------
    transaction_id = generate_transaction_id()

    # --------------------------------------------------------
    # Create payment
    # --------------------------------------------------------
    payment = models.Payment(
        booking_id=booking.id,
        user_id=db_user.id,
        amount=amount,
        status="success",
        method=data.method,
        transaction_id=transaction_id
    )

    db.add(payment)

    # --------------------------------------------------------
    # Update booking payment status
    # --------------------------------------------------------
    booking.payment_status = "paid"

    # --------------------------------------------------------
    # Commit payment + booking status together
    # --------------------------------------------------------
    db.commit()
    db.refresh(payment)

    return payment

# ---------------- GET MY PAYMENTS ----------------
@router.get("/my")
def my_payments(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    db_user = db.query(models.User).filter(
        models.User.username == user["username"]
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    payments = db.query(models.Payment).filter(
        models.Payment.user_id == db_user.id
    ).all()

    return payments


# ---------------- ADMIN: ALL PAYMENTS ----------------
@router.get("/admin")
def all_payments(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    return db.query(models.Payment).all()