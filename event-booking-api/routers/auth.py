from fastapi import APIRouter, Depends, HTTPException, Request
from core.limiter import limiter
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pydantic import BaseModel
import models
import schemas
from services.otp_service import create_otp, verify_otp_code
from services.email_service import send_otp_email
from services.sms_service import send_otp_sms
from core.security import ( hash_password, verify_password, create_token, get_current_user, get_db, normalize_phone, encrypt_phone, decrypt_phone,phone_lookup_hmac,)

router = APIRouter()

def mask_phone(phone: str) -> str:                                                                                       # HELPERS
    if not phone:
        return ""
    if len(phone) <= 4:
        return "*" * len(phone)
    return phone[:3] + "*" * (len(phone) - 7) + phone[-4:]

def get_authenticated_user(user,db: Session):
    db_user = (db.query(models.User).filter(models.User.username == user["username"]).first())
    if not db_user:
        raise HTTPException( status_code=404, detail="User not found")
    if not db_user.is_active:
        raise HTTPException( status_code=403, detail="User account is inactive")
    return db_user

def get_latest_pending_otp(db: Session, user_id: int, purpose: str):
    return (db.query(models.OTPVerification).filter(
            models.OTPVerification.user_id == user_id,
            models.OTPVerification.purpose == purpose,
            models.OTPVerification.verified == False
        )
        .order_by(
            models.OTPVerification.created_at.desc()
        )
        .first()
    )

def get_verified_otp_by_token( db: Session, user_id: int, purpose: str, verification_token: str):
    return (db.query(models.OTPVerification).filter(
            models.OTPVerification.user_id == user_id,
            models.OTPVerification.purpose == purpose,
            models.OTPVerification.verification_token == verification_token,
            models.OTPVerification.verified == True
        )
        .order_by(
            models.OTPVerification.created_at.desc()
        )
        .first()
    )

def check_verification_token_expiry(otp_record):
    expires_at = otp_record.verification_token_expires_at
    if expires_at is None:
        raise HTTPException( status_code=400, detail="Invalid verification token")
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)

    if expires_at <= now:
        raise HTTPException( status_code=400, detail="Verification token has expired")

def consume_verification_token(otp_record):
    otp_record.verification_token = None
    otp_record.verification_token_expires_at = None

@router.post("/register", response_model=schemas.UserResponse)                                                           # REGISTER
@limiter.limit("3/minute")
def register(request: Request, user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = (db.query(models.User).filter(
            (models.User.username == user.username) |
            (models.User.email == user.email)
        )
        .first()
    )
    if existing:
        raise HTTPException( status_code=400, detail="Username or email already exists")
    new_user = models.User(
        username=user.username,
        email=user.email,
        password=hash_password(user.password),
        role="user",
        is_active=True,
        full_name="",
        bio="",
        is_verified=False,
        email_verified=False,
        phone_verified=False,
        phone_encrypted=None,
        phone_lookup_hmac=None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

class LoginRequest(BaseModel):                                                                                           # LOGIN
    username: str
    password: str

@router.post("/login")
def login( request: Request, user: LoginRequest, db: Session = Depends(get_db)):
    db_user = (db.query(models.User).filter(
            (models.User.username == user.username) |
            (models.User.email == user.username)
        )
        .first()
    )
    if not db_user:
        raise HTTPException( status_code=400, detail="Invalid Email/Username or Password")
    if not db_user.is_active:
        raise HTTPException( status_code=403, detail="User account is inactive")
    if not verify_password( user.password, db_user.password):
        raise HTTPException( status_code=400, detail="Invalid Email/Username or Password")
    token = create_token({"sub": db_user.username, "role": db_user.role})
    return {
        "access_token": token,
        "token_type": "bearer"
    }

@router.get("/me")                                                                                                       # PROFILE
def get_profile(user=Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user["username"]).first()
    if not db_user:
        raise HTTPException( status_code=404, detail="User not found")
    bookings_count = db.query(models.Booking).filter( models.Booking.user_id == db_user.id).count()
    phone = None
    if db_user.phone_encrypted:
        try:
            decrypted_phone = decrypt_phone(
                db_user.phone_encrypted
            )
            if len(decrypted_phone) >= 4:                                                                                # Return only masked phone
                phone = ("*" * (len(decrypted_phone) - 4) + decrypted_phone[-4:])
        except ValueError:
            phone = None
    return {
        "username": db_user.username,
        "role": db_user.role,
        "email": db_user.email,
        "phone": phone,
        "phone_verified": db_user.phone_verified,
        "email_verified": db_user.email_verified,
        "is_verified": db_user.is_verified,
        "bookings": bookings_count
    }

@router.post("/otp/send")                                                                                                # SEND OTP
@limiter.limit("5/minute")
def send_otp(request: Request,data: schemas.OTPSendRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = get_authenticated_user(user, db)
    allowed_purposes = {
        "change_username",
        "change_password",
        "change_email",
        "change_phone"
    }
    if data.purpose not in allowed_purposes:
        raise HTTPException(status_code=400, detail="Invalid OTP purpose")
    if data.purpose in {                                                                                                 # CHANGE USERNAME / PASSWORD
        "change_username",
        "change_password"
    }:
        if not db_user.email:
            raise HTTPException(status_code=400,detail="No registered email address found")
        destination = db_user.email

    elif data.purpose == "change_email":                                                                                 # CHANGE EMAIL
        if not data.destination:
            raise HTTPException(status_code=400, detail="New email address is required")
        destination = data.destination.strip().lower()
        existing_email = (db.query(models.User) .filter(models.User.email == destination).first())
        if existing_email and existing_email.id != db_user.id:
            raise HTTPException(status_code=400, detail="Email address is already registered")

    elif data.purpose == "change_phone":                                                                                 # CHANGE PHONE
        if not data.destination:
            raise HTTPException(status_code=400,
                detail="Phone number is required"
            )

        try:
            destination = normalize_phone(
                data.destination
            )

        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc)
            )

        lookup_hash = phone_lookup_hmac(
            destination
        )

        existing_phone = (
            db.query(models.User)
            .filter(
                models.User.phone_lookup_hmac == lookup_hash
            )
            .first()
        )

        if (
            existing_phone
            and existing_phone.id != db_user.id
        ):
            raise HTTPException(
                status_code=400,
                detail="Phone number is already registered"
            )

    # --------------------------------------------------------
    # CREATE OTP
    # --------------------------------------------------------

    otp, otp_record = create_otp(
        db=db,
        user_id=db_user.id,
        purpose=data.purpose,
        destination=destination
    )

    # ========================================================
    # SEND OTP THROUGH THE APPROPRIATE CHANNEL
    # ========================================================

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

    elif data.purpose == "change_phone":

        try:
            send_otp_sms(
                recipient_phone=destination,
                otp=otp
            )


        except Exception as exc:

            otp_record.expires_at = datetime.now(timezone.utc)

            otp_record.used_at = datetime.now(timezone.utc)

            db.commit()

            raise HTTPException(

                status_code=503,

                detail="Unable to send verification SMS"

            ) from exc

    # --------------------------------------------------------
    # PHONE OTP
    #
    # SMS sender will be connected in the next step.
    # The OTP destination is already stored securely in
    # otp_verifications.destination.
    # --------------------------------------------------------

    elif data.purpose == "change_phone":

        # SMS integration goes here.
        #
        # IMPORTANT:
        # Do NOT trust the frontend again during verification.
        # The destination stored in otp_record is authoritative.
        #
        # Example for next step:
        #
        # send_otp_sms(
        #     phone_number=destination,
        #     otp=otp
        # )

        pass

    return {
        "message": "OTP sent successfully"
    }


# ============================================================
# VERIFY OTP
# ============================================================

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

    db_user = get_authenticated_user(user, db)

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

    # --------------------------------------------------------
    # IMPORTANT SECURITY FIX
    #
    # NEVER trust data.destination from the frontend.
    #
    # The backend finds the latest OTP record and gets the
    # destination from the database.
    # --------------------------------------------------------

    otp_record = get_latest_pending_otp(
        db=db,
        user_id=db_user.id,
        purpose=data.purpose
    )

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="OTP not found or already used"
        )

    destination = otp_record.destination

    # --------------------------------------------------------
    # VERIFY OTP
    # --------------------------------------------------------

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


# ============================================================
# CHANGE PHONE
# ============================================================

@router.post("/change-phone")
def change_phone(
    data: schemas.ChangePhoneRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    db_user = get_authenticated_user(user, db)

    # --------------------------------------------------------
    # NORMALIZE NEW PHONE
    # --------------------------------------------------------

    try:
        normalized_phone = normalize_phone(
            data.phone
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    # --------------------------------------------------------
    # FIND VERIFIED OTP TOKEN
    # --------------------------------------------------------

    otp_record = get_verified_otp_by_token(
        db=db,
        user_id=db_user.id,
        purpose="change_phone",
        verification_token=data.verification_token
    )

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification token"
        )

    check_verification_token_expiry(
        otp_record
    )

    # --------------------------------------------------------
    # CRITICAL SECURITY CHECK
    #
    # The phone being changed must be EXACTLY the same phone
    # number for which the OTP was verified.
    # --------------------------------------------------------

    if normalized_phone != otp_record.destination:
        raise HTTPException(
            status_code=400,
            detail="Phone number does not match verified OTP destination"
        )

    # --------------------------------------------------------
    # CHECK DUPLICATE PHONE
    # --------------------------------------------------------

    lookup_hash = phone_lookup_hmac(
        normalized_phone
    )

    existing_phone = (
        db.query(models.User)
        .filter(
            models.User.phone_lookup_hmac == lookup_hash
        )
        .first()
    )

    if (
        existing_phone
        and existing_phone.id != db_user.id
    ):
        raise HTTPException(
            status_code=400,
            detail="Phone number is already registered"
        )

    # --------------------------------------------------------
    # STORE PHONE SECURELY
    # --------------------------------------------------------

    db_user.phone_encrypted = encrypt_phone(
        normalized_phone
    )

    db_user.phone_lookup_hmac = lookup_hash

    # OTP verified the new phone.
    db_user.phone_verified = True

    # --------------------------------------------------------
    # CONSUME VERIFICATION TOKEN
    # --------------------------------------------------------

    consume_verification_token(
        otp_record
    )

    db.commit()
    db.refresh(db_user)

    return {
        "message": "Phone number changed successfully",
        "phone": mask_phone(normalized_phone),
        "phone_verified": True
    }


# ============================================================
# CHANGE PASSWORD
# ============================================================

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

    db_user = get_authenticated_user(user, db)

    otp_record = get_verified_otp_by_token(
        db=db,
        user_id=db_user.id,
        purpose="change_password",
        verification_token=data.verification_token
    )

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification token"
        )

    check_verification_token_expiry(
        otp_record
    )

    # Basic password validation
    if not data.new_password or len(data.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long"
        )

    db_user.password = hash_password(
        data.new_password
    )

    consume_verification_token(
        otp_record
    )

    db.commit()

    return {
        "message": "Password changed successfully"
    }


# ============================================================
# CHANGE EMAIL
# ============================================================

@router.post("/change-email")
@limiter.limit("5/minute")
def change_email(
    request: Request,
    data: schemas.ChangeEmailRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    db_user = get_authenticated_user(user, db)

    new_email = data.email.strip().lower()

    # --------------------------------------------------------
    # CHECK DUPLICATE EMAIL
    # --------------------------------------------------------

    existing_email = (
        db.query(models.User)
        .filter(models.User.email == new_email)
        .first()
    )

    if (
        existing_email
        and existing_email.id != db_user.id
    ):
        raise HTTPException(
            status_code=400,
            detail="Email address is already registered"
        )

    # --------------------------------------------------------
    # FIND VERIFIED OTP
    # --------------------------------------------------------

    otp_record = get_verified_otp_by_token(
        db=db,
        user_id=db_user.id,
        purpose="change_email",
        verification_token=data.verification_token
    )

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification token"
        )

    check_verification_token_expiry(
        otp_record
    )

    # --------------------------------------------------------
    # MAKE SURE EMAIL MATCHES OTP DESTINATION
    # --------------------------------------------------------

    if new_email != otp_record.destination:
        raise HTTPException(
            status_code=400,
            detail="Email address does not match verified OTP destination"
        )

    # --------------------------------------------------------
    # UPDATE EMAIL
    # --------------------------------------------------------

    db_user.email = new_email

    # The new email was verified through OTP.
    db_user.email_verified = True

    consume_verification_token(
        otp_record
    )

    db.commit()
    db.refresh(db_user)

    return {
        "message": "Email changed successfully",
        "email": db_user.email,
        "email_verified": True
    }


# ============================================================
# CHANGE USERNAME
# ============================================================

@router.post("/change-username")
@limiter.limit("5/minute")
def change_username(
    request: Request,
    data: schemas.ChangeUsernameRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    db_user = get_authenticated_user(user, db)

    new_username = data.username.strip()

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CHECK DUPLICATE USERNAME
    # --------------------------------------------------------

    existing_user = (
        db.query(models.User)
        .filter(
            models.User.username == new_username
        )
        .first()
    )

    if (
        existing_user
        and existing_user.id != db_user.id
    ):
        raise HTTPException(
            status_code=400,
            detail="Username is already taken"
        )

    # --------------------------------------------------------
    # FIND VERIFIED OTP
    # --------------------------------------------------------

    otp_record = get_verified_otp_by_token(
        db=db,
        user_id=db_user.id,
        purpose="change_username",
        verification_token=data.verification_token
    )

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification token"
        )

    check_verification_token_expiry(
        otp_record
    )

    # --------------------------------------------------------
    # CHANGE USERNAME
    # --------------------------------------------------------

    old_username = db_user.username

    db_user.username = new_username

    consume_verification_token(
        otp_record
    )

    db.commit()
    db.refresh(db_user)

    return {
        "message": "Username changed successfully",
        "old_username": old_username,
        "username": db_user.username
    }