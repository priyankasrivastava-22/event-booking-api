from fastapi import APIRouter, Depends, HTTPException, status                                      # FASTAPI ROUTING AND HTTP ERRORS
from sqlalchemy.orm import Session                                                                  # SQLALCHEMY DATABASE SESSION
from sqlalchemy.exc import IntegrityError                                                           # DATABASE CONSTRAINT HANDLING
import models                                                                                        # DATABASE MODELS
import schemas                                                                                      # PYDANTIC SCHEMAS
from core.security import get_db, get_current_user                                                    # DATABASE AND AUTH DEPENDENCIES
from utils.helpers import generate_transaction_id                                                     # TRANSACTION ID GENERATOR

router = APIRouter()                                                                                 # PAYMENT ROUTER


def get_authenticated_user(user, db: Session):                                                       # RESOLVE AUTHENTICATED DATABASE USER
    db_user = db.query(models.User).filter(models.User.username == user["username"]).first()         # FIND USER BY JWT SUBJECT
    if not db_user:                                                                                  # VALIDATE USER EXISTENCE
        raise HTTPException(status_code=404, detail="User not found")                               # RETURN USER NOT FOUND
    if not db_user.is_active:                                                                        # VALIDATE ACCOUNT STATUS
        raise HTTPException(status_code=403, detail="User account is inactive")                     # DENY INACTIVE ACCOUNT
    return db_user                                                                                    # RETURN DATABASE USER


def calculate_booking_amount(booking, event):                                                        # CALCULATE SERVER-SIDE BOOKING AMOUNT
    tickets = db_tickets = booking.tickets_rel                                                     # LOAD TICKETS CREATED FOR THIS BOOKING
    if tickets:                                                                                     # USE TICKET SNAPSHOT PRICES FOR NEW ARCHITECTURE
        amount = sum(ticket.price_paid for ticket in tickets if ticket.status != "cancelled")      # SUM IMMUTABLE PRICES STORED ON TICKETS
        if amount > 0:                                                                              # VALIDATE CALCULATED TICKET TOTAL
            return amount                                                                            # RETURN TICKET-BASED TOTAL
    if booking.tickets <= 0:                                                                        # VALIDATE LEGACY BOOKING QUANTITY
        raise HTTPException(status_code=400, detail="Booking contains no tickets")                  # REJECT INVALID BOOKING
    if event.price < 0:                                                                             # VALIDATE EVENT PRICE
        raise HTTPException(status_code=400, detail="Invalid event price")                           # REJECT INVALID PRICE
    return booking.tickets * event.price                                                            # FALLBACK FOR LEGACY GENERAL BOOKINGS


@router.post("/", response_model=schemas.PaymentResponse)                                           # CREATE PAYMENT
def create_payment(data: schemas.PaymentCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):  # CREATE PAYMENT FOR AUTHENTICATED BOOKING
    db_user = get_authenticated_user(user, db)                                                       # RESOLVE AUTHENTICATED USER

    try:                                                                                             # START ATOMIC PAYMENT TRANSACTION
        booking = db.query(models.Booking).filter(models.Booking.id == data.booking_id, models.Booking.user_id == db_user.id).with_for_update().first()  # LOCK USER BOOKING
        if not booking:                                                                             # VALIDATE BOOKING OWNERSHIP
            raise HTTPException(status_code=404, detail="Booking not found")                        # RETURN BOOKING NOT FOUND

        if booking.payment_status == "cancelled":                                                   # PREVENT PAYMENT FOR CANCELLED BOOKING
            raise HTTPException(status_code=400, detail="Cannot pay for a cancelled booking")        # REJECT CANCELLED BOOKING

        if booking.payment_status == "paid":                                                        # PREVENT REPEATED SUCCESSFUL PAYMENT
            existing_payment = db.query(models.Payment).filter(models.Payment.booking_id == booking.id, models.Payment.status == "success").first()  # FIND COMPLETED PAYMENT
            if existing_payment:                                                                     # RETURN EXISTING PAYMENT CONFLICT
                raise HTTPException(status_code=409, detail="Payment already completed for this booking")  # REJECT DUPLICATE PAYMENT
            raise HTTPException(status_code=409, detail="Booking is already marked as paid")        # PROTECT PAYMENT STATE

        existing_payment = db.query(models.Payment).filter(models.Payment.booking_id == booking.id).with_for_update().first()  # CHECK EXISTING PAYMENT RECORD
        if existing_payment and existing_payment.status == "success":                               # PREVENT DUPLICATE SUCCESS PAYMENT
            raise HTTPException(status_code=409, detail="Payment already completed for this booking")  # RETURN PAYMENT CONFLICT

        event = db.query(models.Event).filter(models.Event.id == booking.event_id).first()           # FIND BOOKING EVENT
        if not event:                                                                                # VALIDATE EVENT EXISTENCE
            raise HTTPException(status_code=404, detail="Event not found")                           # RETURN EVENT NOT FOUND

        amount = calculate_booking_amount(booking, event)                                            # CALCULATE PRICE FROM SERVER-SIDE DATA
        if amount <= 0:                                                                              # PREVENT ZERO OR NEGATIVE PAYMENT
            raise HTTPException(status_code=400, detail="Invalid payment amount")                   # REJECT INVALID AMOUNT

        transaction_id = generate_transaction_id()                                                    # GENERATE UNIQUE TRANSACTION IDENTIFIER

        while db.query(models.Payment).filter(models.Payment.transaction_id == transaction_id).first():  # PROTECT AGAINST EXTREMELY RARE ID COLLISION
            transaction_id = generate_transaction_id()                                                # GENERATE ANOTHER TRANSACTION ID

        payment = models.Payment(booking_id=booking.id, user_id=db_user.id, amount=amount, status="success", method=data.method, transaction_id=transaction_id)  # CREATE PAYMENT RECORD

        db.add(payment)                                                                              # ADD PAYMENT TO TRANSACTION
        booking.payment_status = "paid"                                                             # MARK BOOKING AS PAID

        if booking.tickets_rel:                                                                      # UPDATE ASSOCIATED TICKETS
            for ticket in booking.tickets_rel:                                                       # PROCESS EACH BOOKING TICKET
                if ticket.status in {"confirmed", "active", "reserved"}:                            # PRESERVE VALID TICKET STATES
                    ticket.status = "confirmed"                                                     # ENSURE TICKET IS CONFIRMED

        db.commit()                                                                                  # COMMIT PAYMENT AND BOOKING ATOMICALLY
        db.refresh(payment)                                                                          # REFRESH PAYMENT FROM DATABASE
        return payment                                                                               # RETURN CREATED PAYMENT

    except HTTPException:                                                                            # HANDLE EXPECTED BUSINESS ERRORS
        db.rollback()                                                                                # ROLLBACK FAILED TRANSACTION
        raise                                                                                       # PRESERVE ORIGINAL HTTP ERROR

    except IntegrityError as exc:                                                                    # HANDLE DATABASE CONSTRAINT CONFLICTS
        db.rollback()                                                                                # ROLLBACK CONFLICTING TRANSACTION
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment could not be created because a payment already exists") from exc  # RETURN SAFE CONFLICT

    except Exception as exc:                                                                         # HANDLE UNEXPECTED DATABASE ERRORS
        db.rollback()                                                                                # ROLLBACK FAILED TRANSACTION
        raise HTTPException(status_code=500, detail="Unable to process payment") from exc            # RETURN SAFE GENERIC ERROR


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