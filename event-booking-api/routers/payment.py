from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
import schemas

from core.security import get_db, get_current_user
from utils.helpers import generate_transaction_id

router = APIRouter(prefix="/payments", tags=["Payments"])

# ---------------- CREATE PAYMENT ----------------
@router.post("/", response_model=schemas.PaymentResponse)
def create_payment(
    data: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    booking = db.query(models.Booking).filter(
        models.Booking.id == data.booking_id
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    event = db.query(models.Event).filter(
        models.Event.id == booking.event_id
    ).first()

    amount = booking.tickets * event.price

    transaction_id = generate_transaction_id()

    payment = models.Payment(
        booking_id=booking.id,
        user_name=user["username"],
        amount=amount,
        status="success",   # MOCK payment always success
        method=data.method,
        transaction_id=transaction_id
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return payment


# ---------------- GET MY PAYMENTS ----------------
@router.get("/my")
def my_payments(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    payments = db.query(models.Payment).filter(
        models.Payment.user_name == user["username"]
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