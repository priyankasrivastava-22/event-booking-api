from fastapi import APIRouter, Depends, HTTPException, Request
from core.limiter import limiter
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from jose import jwt
from pydantic import BaseModel
import secrets

import models, schemas
from services.otp_service import create_otp, verify_otp_code
from services.email_service import send_otp_email

from core.security import (
    hash_password,
    verify_password,
    create_token,
    get_current_user,
    get_db,
    SECRET_KEY,
    ALGORITHM
)

router = APIRouter()


# ---------------- REGISTER ----------------
@router.post("/register", response_model=schemas.UserResponse)
@limiter.limit("3/minute")
def register(request: Request, user: schemas.UserCreate, db: Session = Depends(get_db)):

    existing = db.query(models.User).filter(
        (models.User.username == user.username) |
        (models.User.email == user.email)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = models.User(
        username=user.username,
        email=user.email,
        password=hash_password(user.password),
        role="user",
        is_active = True,
        is_verified = False,
        full_name="",
        bio=""
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ---------------- LOGIN ----------------
class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(request: Request, user: LoginRequest, db: Session = Depends(get_db)):

    db_user = db.query(models.User).filter(
        (models.User.username == user.username) |
        (models.User.email == user.username)
    ).first()

    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid Email/Username or Password")

    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid Email/Username or Password")

    token = create_token({
        "sub": db_user.username,
        "role": db_user.role
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }
class ChangePasswordRequest(BaseModel):
    verification_token: str
    new_password: str

# ---------------- PROFILE ----------------
@router.get("/me")
def get_profile(user=Depends(get_current_user), db: Session = Depends(get_db)):

    bookings_count = db.query(models.Booking).filter(
        models.Booking.user_name == user["username"]
    ).count()

    return {
        "username": user["username"],
        "role": user["role"],
        "bookings": bookings_count
    }

# ---------------- SEND OTP ----------------
@router.post("/otp/send")
@limiter.limit("5/minute")
def send_otp(
    request: Request,
    data: schemas.OTPSendRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find the actual database user
    db_user = db.query(models.User).filter(
        models.User.username == user["username"]
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Only allow supported OTP purposes
    allowed_purposes = {
        "change_username",
        "change_password",
        "change_email",
        "change_phone"
    }

    if data.purpose not in allowed_purposes:
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP purpose"
        )

    # Determine where OTP should be sent
    if data.purpose in {
        "change_username",
        "change_password"
    }:
        destination = db_user.email

        if not destination:
            raise HTTPException(
                status_code=400,
                detail="No registered email address found"
            )

    elif data.purpose == "change_email":
        if not data.destination:
            raise HTTPException(
                status_code=400,
                detail="New email address is required"
            )

        destination = data.destination

        # Prevent duplicate email
        existing_email = db.query(models.User).filter(
            models.User.email == destination
        ).first()

        if existing_email and existing_email.id != db_user.id:
            raise HTTPException(
                status_code=400,
                detail="Email address is already registered"
            )

    elif data.purpose == "change_phone":
        if not data.destination:
            raise HTTPException(
                status_code=400,
                detail="Phone number is required"
            )

        destination = data.destination

        # Prevent duplicate phone
        existing_phone = db.query(models.User).filter(
            models.User.phone == destination
        ).first()

        if existing_phone and existing_phone.id != db_user.id:
            raise HTTPException(
                status_code=400,
                detail="Phone number is already registered"
            )

    # Generate and store OTP
    otp, otp_record = create_otp(
        db=db,
        user_id=db_user.id,
        purpose=data.purpose,
        destination=destination
    )

    # Currently our email service sends OTP through email.
    # Phone/SMS integration will be added separately.
    if data.purpose in {
        "change_username",
        "change_password",
        "change_email"
    }:
        send_otp_email(
            recipient_email=destination,
            otp=otp,
            purpose=data.purpose
        )

    return {
        "message": "OTP sent successfully"
    }

# ---------------- VERIFY OTP ----------------
@router.post(
    "/otp/verify",
    response_model=schemas.OTPVerifyResponse
)
@limiter.limit("5/minute")
def verify_otp_endpoint(
    request: Request,
    data: schemas.OTPVerifyRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # Find the logged-in user
    db_user = db.query(models.User).filter(
        models.User.username == user["username"]
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Determine the destination used for the OTP
    destination = data.destination

    if not destination:

        if data.purpose == "change_password":
            destination = db_user.email

        elif data.purpose == "change_username":
            destination = db_user.email

        elif data.purpose == "change_email":
            destination = db_user.email

        elif data.purpose == "change_phone":
            destination = db_user.phone

    if not destination:
        raise HTTPException(
            status_code=400,
            detail="No destination available for OTP verification"
        )

    # Verify OTP
    success, message, verification_token = verify_otp_code(
        db=db,
        user_id=db_user.id,
        purpose=data.purpose,
        otp=data.otp,
        destination=destination
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail=message
        )

    return {
        "message": message,
        "verification_token": verification_token
    }

# ---------------- CHANGE PHONE ----------------

@router.post("/change-phone")
def change_phone(
    data: schemas.ChangePhoneRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get the currently authenticated user
    db_user = db.query(models.User).filter(
        models.User.username == user["username"]
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    new_phone = data.phone.strip()

    # Basic validation
    if not new_phone:
        raise HTTPException(
            status_code=400,
            detail="Phone number cannot be empty"
        )

    # Basic length validation
    if len(new_phone) < 10 or len(new_phone) > 15:
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number"
        )

    # Check whether the phone number is already registered
    existing_phone = db.query(models.User).filter(
        models.User.phone == new_phone
    ).first()

    if existing_phone and existing_phone.id != db_user.id:
        raise HTTPException(
            status_code=400,
            detail="Phone number is already registered"
        )

    # Find the verified OTP record that generated this token
    otp_record = db.query(models.OTPVerification).filter(
        models.OTPVerification.user_id == db_user.id,
        models.OTPVerification.purpose == "change_phone",
        models.OTPVerification.verification_token == data.verification_token,
        models.OTPVerification.verified == True
    ).order_by(
        models.OTPVerification.created_at.desc()
    ).first()

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification token"
        )

    # Check verification token expiry
    now = datetime.now(timezone.utc)

    token_expires_at = otp_record.verification_token_expires_at

    if token_expires_at is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification token"
        )

    if token_expires_at.tzinfo is None:
        token_expires_at = token_expires_at.replace(
            tzinfo=timezone.utc
        )

    if token_expires_at < now:
        raise HTTPException(
            status_code=400,
            detail="Verification token has expired"
        )

    # Update phone
    db_user.phone = new_phone

    # New phone has NOT been independently verified yet
    db_user.phone_verified = False

    # Consume verification token
    otp_record.verification_token = None
    otp_record.verification_token_expires_at = None

    db.commit()
    db.refresh(db_user)

    return {
        "message": "Phone number changed successfully",
        "phone": db_user.phone,
        "phone_verified": db_user.phone_verified
    }

# ---------------- CHANGE PASSWORD ----------------

class ChangePasswordRequest(BaseModel):
    verification_token: str
    new_password: str


@router.post("/change-password")
@limiter.limit("5/minute")
def change_password(
    request: Request,
    data: ChangePasswordRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # Find logged-in user
    db_user = db.query(models.User).filter(
        models.User.username == user["username"]
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Find the OTP verification record
    otp_record = (
        db.query(models.OTPVerification)
        .filter(
            models.OTPVerification.user_id == db_user.id,
            models.OTPVerification.purpose == "change_password",
            models.OTPVerification.verification_token == data.verification_token
        )
        .order_by(
            models.OTPVerification.created_at.desc()
        )
        .first()
    )

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification token"
        )

    # Verification token must have an expiry
    expires_at = otp_record.verification_token_expires_at

    if expires_at is None:
        raise HTTPException(
            status_code=400,
            detail="Verification token has no expiry"
        )

    # Handle PostgreSQL returning a naive datetime
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    now = datetime.now(timezone.utc)

    # Check expiry
    if expires_at < now:
        raise HTTPException(
            status_code=400,
            detail="Verification token has expired"
        )

    # Change password
    db_user.password = hash_password(data.new_password)

    # Invalidate the verification token
    otp_record.verification_token = None
    otp_record.verification_token_expires_at = None

    db.commit()

    return {
        "message": "Password changed successfully"
    }

# ---------------- CHANGE EMAIL ----------------

@router.post("/change-email")
@limiter.limit("5/minute")
def change_email(
    request: Request,
    data: schemas.ChangeEmailRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # Find logged-in user
    db_user = db.query(models.User).filter(
        models.User.username == user["username"]
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Check whether the new email is already registered
    existing_email = db.query(models.User).filter(
        models.User.email == data.email
    ).first()

    if existing_email and existing_email.id != db_user.id:
        raise HTTPException(
            status_code=400,
            detail="Email address is already registered"
        )

    # Find the verified OTP record using the verification token
    otp_record = (
        db.query(models.OTPVerification)
        .filter(
            models.OTPVerification.user_id == db_user.id,
            models.OTPVerification.purpose == "change_email",
            models.OTPVerification.verification_token == data.verification_token
        )
        .order_by(
            models.OTPVerification.created_at.desc()
        )
        .first()
    )

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification token"
        )

    # Check verification token expiry
    expires_at = otp_record.verification_token_expires_at

    if expires_at is None:
        raise HTTPException(
            status_code=400,
            detail="Verification token has no expiry"
        )

    # PostgreSQL may return a naive datetime
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    now = datetime.now(timezone.utc)

    if expires_at < now:
        raise HTTPException(
            status_code=400,
            detail="Verification token has expired"
        )

    # Make sure OTP was actually verified
    if not otp_record.verified:
        raise HTTPException(
            status_code=400,
            detail="OTP verification required"
        )

    # Update email
    db_user.email = data.email

    # New email is not considered separately verified
    db_user.email_verified = True

    # Invalidate verification token
    otp_record.verification_token = None
    otp_record.verification_token_expires_at = None

    db.commit()
    db.refresh(db_user)

    return {
        "message": "Email changed successfully",
        "email": db_user.email
    }

# ---------------- CHANGE USERNAME ----------------

@router.post("/change-username")
def change_username(
    data: schemas.ChangeUsernameRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get the currently authenticated user
    db_user = db.query(models.User).filter(
        models.User.username == user["username"]
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    new_username = data.username.strip()

    # Basic validation
    if not new_username:
        raise HTTPException(
            status_code=400,
            detail="Username cannot be empty"
        )

    if len(new_username) < 3 or len(new_username) > 50:
        raise HTTPException(
            status_code=400,
            detail="Username must be between 3 and 50 characters"
        )

    # Check whether username is already taken
    existing_user = db.query(models.User).filter(
        models.User.username == new_username
    ).first()

    if existing_user and existing_user.id != db_user.id:
        raise HTTPException(
            status_code=400,
            detail="Username is already taken"
        )

    # Find the OTP record that generated this verification token
    otp_record = db.query(models.OTPVerification).filter(
        models.OTPVerification.user_id == db_user.id,
        models.OTPVerification.purpose == "change_username",
        models.OTPVerification.verification_token == data.verification_token,
        models.OTPVerification.verified == True
    ).order_by(
        models.OTPVerification.created_at.desc()
    ).first()

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification token"
        )

    # Check token expiry
    now = datetime.now(timezone.utc)

    token_expires_at = otp_record.verification_token_expires_at

    if token_expires_at is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification token"
        )

    # PostgreSQL may return a naive datetime depending on configuration
    if token_expires_at.tzinfo is None:
        token_expires_at = token_expires_at.replace(
            tzinfo=timezone.utc
        )

    if token_expires_at < now:
        raise HTTPException(
            status_code=400,
            detail="Verification token has expired"
        )

    # Change username
    old_username = db_user.username
    db_user.username = new_username

    # Consume the verification token
    otp_record.verification_token = None
    otp_record.verification_token_expires_at = None

    db.commit()
    db.refresh(db_user)

    return {
        "message": "Username changed successfully",
        "old_username": old_username,
        "username": db_user.username
    }