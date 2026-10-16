import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status                                      # FASTAPI ROUTING AND HTTP ERRORS
from sqlalchemy.orm import Session                                                                  # SQLALCHEMY DATABASE SESSION
from sqlalchemy.exc import IntegrityError                                                           # DATABASE CONSTRAINT HANDLING
import models                                                                                        # DATABASE MODELS
import schemas                                                                                      # PYDANTIC SCHEMAS
from utils.helpers import get_db
from core.security import get_current_user
from services.booking_service import BookingService                                                    # DATABASE AND AUTH DEPENDENCIES
from utils.helpers import generate_transaction_id                                                     # TRANSACTION ID GENERATOR

router = APIRouter()                                                                                 # PAYMENT ROUTER


def get_authenticated_user(user, db: Session):                                                       # RESOLVE AUTHENTICATED DATABASE USER
    db_user = db.query(models.User).filter(models.User.username == user["username"]).first()         # FIND USER BY JWT SUBJECT
    if not db_user:                                                                                  # VALIDATE USER EXISTENCE
        raise HTTPException(status_code=404, detail="User not found")                               # RETURN USER NOT FOUND
    if not db_user.is_active:                                                                        # VALIDATE ACCOUNT STATUS
        raise HTTPException(status_code=403, detail="User account is inactive")                     # DENY INACTIVE ACCOUNT
    return db_user                                                                                    # RETURN DATABASE USER


def calculate_booking_amount(booking, event):
    """Charge server-side, snapshotted BookingItem prices, never a client total."""
    items = [item for item in booking.items if item.status == models.BOOKING_HELD]
    if items:
        return sum(item.price * item.quantity for item in items)
    # Compatibility for already-issued legacy tickets only.
    if booking.tickets_rel:
        return sum(t.price_paid for t in booking.tickets_rel if t.status != models.TICKET_CANCELLED)
    raise HTTPException(status_code=400, detail="Booking contains no held tickets")


@router.post("/", response_model=schemas.PaymentResponse)
def create_payment(data: schemas.PaymentCreate, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    """MOCK payment ONLY. No real money is taken by this endpoint.

    On successful mock checkout, payment, inventory sale, tickets and booking
    confirmation are one database transaction. Replace mock success with a
    verified payment-provider webhook before accepting actual money.
    """
    db_user = get_authenticated_user(user, db)
    if os.getenv("ENABLE_MOCK_PAYMENTS", "false").lower() != "true":
        raise HTTPException(status_code=503, detail="Demo payments are disabled; configure a verified payment gateway for production")
    if data.method != "mock":
        raise HTTPException(status_code=422, detail="Only mock payment is implemented; no real card or UPI payment is processed")
    try:
        booking = (db.query(models.Booking)
                   .filter(models.Booking.id == data.booking_id,
                           models.Booking.user_id == db_user.id)
                   .with_for_update().first())
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        if booking.status == models.BOOKING_CONFIRMED or booking.payment_status == "paid":
            paid = db.query(models.Payment).filter_by(booking_id=booking.id, user_id=db_user.id).first()
            if paid and paid.status == models.PAYMENT_SUCCESS:
                return paid  # Retry after a dropped response must never charge or issue twice.
            raise HTTPException(status_code=409, detail="Booking has already been confirmed")
        if booking.status != models.BOOKING_HELD:
            raise HTTPException(status_code=409, detail="Booking no longer has a valid hold")
        existing_payment = db.query(models.Payment.id).filter_by(booking_id=booking.id).first()
        if existing_payment:
            raise HTTPException(status_code=409, detail="Payment already exists for this booking")
        event = db.get(models.Event, booking.event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        amount = calculate_booking_amount(booking, event)
        if amount < 0 or amount != booking.total_amount:
            raise HTTPException(status_code=409, detail="Booking total has changed; restart checkout")

        # Mock-only success: no external payment is processed here.
        service = BookingService(db)
        service.confirm_booking(booking_id=booking.id, user_id=db_user.id, commit=False)
        transaction_id = generate_transaction_id()
        while db.query(models.Payment.id).filter_by(transaction_id=transaction_id).first():
            transaction_id = generate_transaction_id()
        payment = models.Payment(booking_id=booking.id, user_id=db_user.id,
                                 amount=amount, status=models.PAYMENT_SUCCESS,
                                 method="mock", provider="mock", paid_at=datetime.now(timezone.utc),
                                 transaction_id=transaction_id)
        db.add(payment)
        booking.payment_status = "paid"
        db.add(models.Notification(user_id=db_user.id,
                    message=f"Booking #{booking.id} confirmed: {booking.tickets} ticket(s) for {event.title}."))
        db.commit()
        db.refresh(payment)
        return payment
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Concurrent payment already exists") from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to complete mock checkout") from exc


@router.get("/my", response_model=list[schemas.PaymentResponse])                                    # GET AUTHENTICATED USER PAYMENTS
def my_payments(db: Session = Depends(get_db), user=Depends(get_current_user)):                     # FETCH CURRENT USER PAYMENTS
    db_user = get_authenticated_user(user, db)                                                       # RESOLVE AUTHENTICATED USER
    payments = db.query(models.Payment).filter(models.Payment.user_id == db_user.id).order_by(models.Payment.created_at.desc()).all()  # FETCH PAYMENTS NEWEST FIRST
    return payments                                                                                  # RETURN USER PAYMENT HISTORY


@router.get("/my/{payment_id}", response_model=schemas.PaymentResponse)                              # GET SINGLE USER PAYMENT
def get_my_payment(payment_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)): # FETCH OWN PAYMENT
    db_user = get_authenticated_user(user, db)                                                       # RESOLVE AUTHENTICATED USER
    payment = db.query(models.Payment).filter(models.Payment.id == payment_id, models.Payment.user_id == db_user.id).first()  # FIND OWN PAYMENT
    if not payment:                                                                                  # VALIDATE PAYMENT EXISTENCE
        raise HTTPException(status_code=404, detail="Payment not found")                            # RETURN PAYMENT NOT FOUND
    return payment                                                                                    # RETURN PAYMENT


@router.get("/admin", response_model=list[schemas.PaymentResponse])                                  # ADMIN PAYMENT HISTORY
def all_payments(db: Session = Depends(get_db), user=Depends(get_current_user)):                    # FETCH ALL PAYMENTS FOR ADMIN
    if user["role"] != "admin":                                                                      # VALIDATE ADMIN ROLE
        raise HTTPException(status_code=403, detail="Only admin allowed")                           # DENY NON-ADMIN USER
    return db.query(models.Payment).order_by(models.Payment.created_at.desc()).all()                # RETURN PAYMENTS NEWEST FIRST