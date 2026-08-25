from fastapi import APIRouter, Depends, HTTPException, Request, status                                      # FASTAPI ROUTING AND REQUEST HANDLING
from core.limiter import limiter                                                                              # API RATE LIMITING
from sqlalchemy.orm import Session                                                                            # SQLALCHEMY DATABASE SESSION
from datetime import datetime, timezone                                                                       # UTC DATE AND TIME UTILITIES
from pydantic import BaseModel, Field                                                                         # PYDANTIC REQUEST VALIDATION

import models                                                                                                 # DATABASE MODELS
import schemas                                                                                                 # PYDANTIC SCHEMAS

from services.otp_service import create_otp, verify_otp_code                                                   # OTP CREATION AND VERIFICATION
from services.email_service import send_otp_email                                                             # EMAIL OTP DELIVERY
from services.sms_service import send_otp_sms                                                                 # SMS OTP DELIVERY
from core.security import (hash_password, verify_password, create_token, get_current_user, get_db, normalize_phone, encrypt_phone, decrypt_phone, phone_lookup_hmac)  # SECURITY AND DATABASE HELPERS


router = APIRouter()                                                                                           # AUTHENTICATION ROUTER


def mask_phone(phone: str) -> str:                                                                             # PHONE MASKING HELPER
    if not phone:                                                                                              # HANDLE EMPTY PHONE
        return ""                                                                                              # RETURN EMPTY VALUE
    if len(phone) <= 4:                                                                                        # HANDLE SHORT PHONE VALUES
        return "*" * len(phone)                                                                                # MASK ENTIRE VALUE
    return phone[:3] + "*" * (len(phone) - 7) + phone[-4:]                                                     # PRESERVE PREFIX AND LAST FOUR DIGITS


def get_authenticated_user(user, db: Session):                                                                 # LOAD AND VALIDATE AUTHENTICATED USER
    username = user.get("username") if isinstance(user, dict) else getattr(user, "username", None)           # SUPPORT CURRENT TOKEN PAYLOAD FORMAT
    if not username:                                                                                            # VALIDATE AUTHENTICATION IDENTITY
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")  # REJECT INVALID IDENTITY
    db_user = db.query(models.User).filter(models.User.username == username).first()                         # FIND USER BY IMMUTABLE LOGIN IDENTITY
    if not db_user:                                                                                             # VALIDATE USER EXISTENCE
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")                   # RETURN USER NOT FOUND
    if not db_user.is_active:                                                                                   # VALIDATE ACCOUNT STATUS
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")         # BLOCK INACTIVE ACCOUNT
    return db_user                                                                                              # RETURN DATABASE USER


def get_latest_pending_otp(db: Session, user_id: int, purpose: str):                                           # FIND LATEST UNUSED OTP
    return db.query(models.OTPVerification).filter(models.OTPVerification.user_id == user_id, models.OTPVerification.purpose == purpose, models.OTPVerification.verified == False).order_by(models.OTPVerification.created_at.desc()).first()  # RETURN MOST RECENT PENDING OTP


def get_verified_otp_by_token(db: Session, user_id: int, purpose: str, verification_token: str):              # FIND VERIFIED OTP TOKEN
    return db.query(models.OTPVerification).filter(models.OTPVerification.user_id == user_id, models.OTPVerification.purpose == purpose, models.OTPVerification.verification_token == verification_token, models.OTPVerification.verified == True).order_by(models.OTPVerification.created_at.desc()).first()  # RETURN VERIFIED TOKEN


def check_verification_token_expiry(otp_record):                                                               # VERIFY POST-OTP TOKEN EXPIRATION
    expires_at = otp_record.verification_token_expires_at                                                     # READ TOKEN EXPIRATION
    if expires_at is None:                                                                                     # VALIDATE TOKEN EXPIRATION
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")    # REJECT INVALID TOKEN
    if expires_at.tzinfo is None:                                                                              # NORMALIZE NAIVE DATABASE TIMESTAMP
        expires_at = expires_at.replace(tzinfo=timezone.utc)                                                   # TREAT NAIVE TIMESTAMP AS UTC
    now = datetime.now(timezone.utc)                                                                           # GET CURRENT UTC TIME
    if expires_at <= now:                                                                                      # CHECK TOKEN EXPIRATION
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification token has expired") # REJECT EXPIRED TOKEN


def consume_verification_token(otp_record):                                                                    # INVALIDATE VERIFIED OTP TOKEN AFTER USE
    otp_record.verification_token = None                                                                       # REMOVE VERIFICATION TOKEN
    otp_record.verification_token_expires_at = None                                                            # REMOVE TOKEN EXPIRATION


@router.post("/register", response_model=schemas.UserResponse)                                                 # REGISTER USER
@limiter.limit("3/minute")                                                                                     # LIMIT REGISTRATION ATTEMPTS
def register(request: Request, user: schemas.UserCreate, db: Session = Depends(get_db)):                      # CREATE NEW USER ACCOUNT
    username = user.username.strip()                                                                            # NORMALIZE USERNAME
    email = user.email.strip().lower() if user.email else None                                                 # NORMALIZE EMAIL
    if not username:                                                                                            # VALIDATE USERNAME
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username cannot be empty")       # REJECT EMPTY USERNAME
    if email is None:                                                                                           # VALIDATE EMAIL
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required")              # REJECT EMPTY EMAIL
    existing = db.query(models.User).filter((models.User.username == username) | (models.User.email == email)).first()  # CHECK EXISTING USERNAME OR EMAIL
    if existing:                                                                                               # PREVENT DUPLICATE ACCOUNT
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already exists") # RETURN DUPLICATE ERROR
    new_user = models.User(username=username, email=email, password=hash_password(user.password), role="user", is_active=True, full_name="", bio="", is_verified=False, email_verified=False, phone_verified=False, phone_encrypted=None, phone_lookup_hmac=None)  # CREATE USER WITH SAFE DEFAULTS
    try:                                                                                                       # START ATOMIC USER CREATION
        db.add(new_user)                                                                                        # ADD USER TO TRANSACTION
        db.commit()                                                                                             # COMMIT USER
        db.refresh(new_user)                                                                                    # LOAD GENERATED DATABASE VALUES
    except Exception:                                                                                           # HANDLE DATABASE FAILURE
        db.rollback()                                                                                           # ROLLBACK USER CREATION
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to create account")  # RETURN SAFE DATABASE ERROR
    return new_user                                                                                             # RETURN CREATED USER


class LoginRequest(BaseModel):                                                                                  # LOGIN REQUEST
    username: str = Field(min_length=1, max_length=255)                                                       # USERNAME OR EMAIL
    password: str = Field(min_length=1, max_length=128)                                                       # USER PASSWORD


@router.post("/login")                                                                                          # USER LOGIN
@limiter.limit("5/minute")                                                                                     # LIMIT LOGIN ATTEMPTS
def login(request: Request, user: LoginRequest, db: Session = Depends(get_db)):                               # AUTHENTICATE USER
    login_identity = user.username.strip()                                                                      # NORMALIZE LOGIN IDENTITY
    db_user = db.query(models.User).filter((models.User.username == login_identity) | (models.User.email == login_identity.lower())).first()  # FIND USER BY USERNAME OR EMAIL
    if not db_user:                                                                                             # VALIDATE USER EXISTENCE
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Email/Username or Password")  # RETURN GENERIC LOGIN ERROR
    if not db_user.is_active:                                                                                   # VALIDATE ACCOUNT STATUS
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")         # BLOCK INACTIVE ACCOUNT
    if not verify_password(user.password, db_user.password):                                                   # VERIFY PASSWORD HASH
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Email/Username or Password")  # RETURN GENERIC LOGIN ERROR
    token = create_token({"sub": db_user.username, "role": db_user.role})                                     # CREATE JWT ACCESS TOKEN
    return {"access_token": token, "token_type": "bearer"}                                                    # RETURN BEARER TOKEN


@router.get("/me")                                                                                             # CURRENT USER PROFILE
def get_profile(user=Depends(get_current_user), db: Session = Depends(get_db)):                               # RETURN AUTHENTICATED USER INFORMATION
    db_user = get_authenticated_user(user, db)                                                                  # LOAD ACTIVE USER
    bookings_count = db.query(models.Booking).filter(models.Booking.user_id == db_user.id).count()             # COUNT USER BOOKINGS USING USER ID
    phone = None                                                                                                # DEFAULT MASKED PHONE
    if db_user.phone_encrypted:                                                                                 # CHECK STORED ENCRYPTED PHONE
        try:                                                                                                   # SAFELY DECRYPT PHONE
            decrypted_phone = decrypt_phone(db_user.phone_encrypted)                                          # DECRYPT PHONE NUMBER
            phone = mask_phone(decrypted_phone)                                                                # RETURN ONLY MASKED PHONE
        except (ValueError, TypeError):                                                                         # HANDLE INVALID ENCRYPTED DATA
            phone = None                                                                                        # NEVER EXPOSE PHONE DATA ON DECRYPTION FAILURE
    return {"username": db_user.username, "role": db_user.role, "email": db_user.email, "phone": phone, "phone_verified": db_user.phone_verified, "email_verified": db_user.email_verified, "is_verified": db_user.is_verified, "bookings": bookings_count}  # RETURN PROFILE DATA


@router.post("/otp/send")                                                                                      # SEND OTP
@limiter.limit("5/minute")                                                                                     # LIMIT OTP SEND REQUESTS
def send_otp(request: Request, data: schemas.OTPSendRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):  # SEND OTP TO VERIFIED USER
    db_user = get_authenticated_user(user, db)                                                                  # LOAD ACTIVE USER
    allowed_purposes = {"change_username", "change_password", "change_email", "change_phone"}                 # SUPPORTED OTP PURPOSES
    if data.purpose not in allowed_purposes:                                                                    # VALIDATE OTP PURPOSE
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP purpose")            # REJECT UNSUPPORTED PURPOSE
    if data.purpose in {"change_username", "change_password"}:                                                 # PASSWORD AND USERNAME CHANGE OTP
        if not db_user.email:                                                                                   # REQUIRE REGISTERED EMAIL
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No registered email address found")  # RETURN MISSING EMAIL ERROR
        destination = db_user.email.strip().lower()                                                            # USE REGISTERED EMAIL
    elif data.purpose == "change_email":                                                                        # CHANGE EMAIL OTP
        if not data.destination:                                                                                # REQUIRE NEW EMAIL
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New email address is required")  # RETURN MISSING EMAIL ERROR
        destination = data.destination.strip().lower()                                                         # NORMALIZE NEW EMAIL
        existing_email = db.query(models.User).filter(models.User.email == destination).first()               # CHECK EMAIL UNIQUENESS
        if existing_email and existing_email.id != db_user.id:                                                # PREVENT EMAIL REUSE
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email address is already registered")  # RETURN DUPLICATE EMAIL ERROR
    else:                                                                                                      # CHANGE PHONE OTP
        if not data.destination:                                                                                # REQUIRE NEW PHONE
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number is required")  # RETURN MISSING PHONE ERROR
        try:                                                                                                   # NORMALIZE PHONE
            destination = normalize_phone(data.destination)                                                     # CREATE CANONICAL PHONE NUMBER
        except ValueError as exc:                                                                               # HANDLE INVALID PHONE
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc             # RETURN PHONE VALIDATION ERROR
        lookup_hash = phone_lookup_hmac(destination)                                                           # CREATE NON-REVERSIBLE PHONE LOOKUP HASH
        existing_phone = db.query(models.User).filter(models.User.phone_lookup_hmac == lookup_hash).first()   # CHECK PHONE UNIQUENESS
        if existing_phone and existing_phone.id != db_user.id:                                                # PREVENT PHONE REUSE
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number is already registered")  # RETURN DUPLICATE PHONE ERROR
    otp, otp_record = create_otp(db=db, user_id=db_user.id, purpose=data.purpose, destination=destination)    # CREATE AND STORE OTP
    if data.purpose in {"change_username", "change_password", "change_email"}:                                # EMAIL OTP DELIVERY
        try:                                                                                                   # HANDLE EMAIL DELIVERY FAILURE
            send_otp_email(recipient_email=destination, otp=otp, purpose=data.purpose)                       # SEND OTP THROUGH EMAIL
        except Exception as exc:                                                                               # HANDLE EMAIL SERVICE FAILURE
            otp_record.expires_at = datetime.now(timezone.utc)                                                # INVALIDATE OTP
            otp_record.used_at = datetime.now(timezone.utc)                                                   # MARK OTP AS USED
            db.commit()                                                                                        # SAVE INVALIDATED OTP
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Unable to send verification email") from exc  # RETURN SERVICE ERROR
    else:                                                                                                     # SMS OTP DELIVERY
        try:                                                                                                   # HANDLE SMS DELIVERY FAILURE
            send_otp_sms(recipient_phone=destination, otp=otp)                                                # SEND OTP THROUGH SMS
        except Exception as exc:                                                                               # HANDLE SMS SERVICE FAILURE
            otp_record.expires_at = datetime.now(timezone.utc)                                                # INVALIDATE OTP
            otp_record.used_at = datetime.now(timezone.utc)                                                   # MARK OTP AS USED
            db.commit()                                                                                        # SAVE INVALIDATED OTP
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Unable to send verification SMS") from exc  # RETURN SERVICE ERROR
    return {"message": "OTP sent successfully"}                                                               # CONFIRM OTP DELIVERY


@router.post("/otp/verify", response_model=schemas.OTPVerifyResponse)                                          # VERIFY OTP
@limiter.limit("5/minute")                                                                                     # LIMIT OTP VERIFICATION ATTEMPTS
def verify_otp_endpoint(request: Request, data: schemas.OTPVerifyRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):  # VERIFY USER OTP
    db_user = get_authenticated_user(user, db)                                                                  # LOAD ACTIVE USER
    allowed_purposes = {"change_username", "change_password", "change_email", "change_phone"}                 # SUPPORTED OTP PURPOSES
    if data.purpose not in allowed_purposes:                                                                    # VALIDATE OTP PURPOSE
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP purpose")            # REJECT INVALID PURPOSE
    otp_record = get_latest_pending_otp(db=db, user_id=db_user.id, purpose=data.purpose)                     # LOAD LATEST PENDING OTP
    if not otp_record:                                                                                          # VALIDATE OTP EXISTENCE
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP not found or already used")  # RETURN INVALID OTP ERROR
    destination = otp_record.destination                                                                        # USE ORIGINAL OTP DESTINATION
    success, message, verification_token = verify_otp_code(db=db, user_id=db_user.id, purpose=data.purpose, otp=data.otp, destination=destination)  # VERIFY OTP AND ISSUE SHORT-LIVED TOKEN
    if not success:                                                                                             # VALIDATE OTP RESULT
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)                          # RETURN OTP FAILURE
    return {"message": message, "verification_token": verification_token}                                    # RETURN ONE-TIME VERIFICATION TOKEN


@router.post("/change-phone")                                                                                  # CHANGE PHONE NUMBER
@limiter.limit("5/minute")                                                                                     # LIMIT SENSITIVE ACCOUNT CHANGES
def change_phone(request: Request, data: schemas.ChangePhoneRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):  # APPLY VERIFIED PHONE CHANGE
    db_user = get_authenticated_user(user, db)                                                                  # LOAD ACTIVE USER
    try:                                                                                                       # NORMALIZE NEW PHONE
        normalized_phone = normalize_phone(data.phone)                                                         # CREATE CANONICAL PHONE VALUE
    except ValueError as exc:                                                                                   # HANDLE INVALID PHONE
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc                 # RETURN PHONE VALIDATION ERROR
    otp_record = get_verified_otp_by_token(db=db, user_id=db_user.id, purpose="change_phone", verification_token=data.verification_token)  # FIND VERIFIED PHONE OTP
    if not otp_record:                                                                                          # VALIDATE VERIFICATION TOKEN
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")    # REJECT INVALID TOKEN
    check_verification_token_expiry(otp_record)                                                                # VALIDATE TOKEN EXPIRATION
    if normalized_phone != otp_record.destination:                                                              # ENSURE OTP WAS FOR SAME PHONE
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number does not match verified OTP destination")  # REJECT MISMATCH
    lookup_hash = phone_lookup_hmac(normalized_phone)                                                          # CREATE PHONE LOOKUP HASH
    existing_phone = db.query(models.User).filter(models.User.phone_lookup_hmac == lookup_hash).first()       # CHECK PHONE UNIQUENESS
    if existing_phone and existing_phone.id != db_user.id:                                                    # PREVENT PHONE REUSE
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number is already registered")  # RETURN DUPLICATE ERROR
    db_user.phone_encrypted = encrypt_phone(normalized_phone)                                                 # STORE ENCRYPTED PHONE
    db_user.phone_lookup_hmac = lookup_hash                                                                    # STORE SEARCHABLE HMAC
    db_user.phone_verified = True                                                                               # MARK PHONE VERIFIED
    consume_verification_token(otp_record)                                                                      # CONSUME ONE-TIME TOKEN
    try:                                                                                                       # START ACCOUNT UPDATE
        db.commit()                                                                                             # COMMIT PHONE CHANGE
        db.refresh(db_user)                                                                                    # REFRESH USER
    except Exception:                                                                                           # HANDLE DATABASE FAILURE
        db.rollback()                                                                                           # ROLLBACK PHONE CHANGE
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to change phone number")  # RETURN SAFE ERROR
    return {"message": "Phone number changed successfully", "phone": mask_phone(normalized_phone), "phone_verified": True}  # RETURN UPDATED PHONE STATUS


class ChangePasswordRequest(BaseModel):                                                                         # CHANGE PASSWORD REQUEST
    verification_token: str = Field(min_length=1)                                                              # VERIFIED OTP TOKEN
    new_password: str = Field(min_length=8, max_length=128)                                                    # NEW PASSWORD


@router.post("/change-password")                                                                               # CHANGE PASSWORD
@limiter.limit("5/minute")                                                                                     # LIMIT SENSITIVE ACCOUNT CHANGES
def change_password(request: Request, data: ChangePasswordRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):  # APPLY VERIFIED PASSWORD CHANGE
    db_user = get_authenticated_user(user, db)                                                                  # LOAD ACTIVE USER
    otp_record = get_verified_otp_by_token(db=db, user_id=db_user.id, purpose="change_password", verification_token=data.verification_token)  # FIND VERIFIED PASSWORD OTP
    if not otp_record:                                                                                          # VALIDATE VERIFICATION TOKEN
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")    # REJECT INVALID TOKEN
    check_verification_token_expiry(otp_record)                                                                # VALIDATE TOKEN EXPIRATION
    if not data.new_password or len(data.new_password) < 8:                                                    # VALIDATE PASSWORD LENGTH
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters long")  # RETURN PASSWORD ERROR
    if verify_password(data.new_password, db_user.password):                                                   # PREVENT PASSWORD REUSE
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different from the current password")  # REJECT SAME PASSWORD
    db_user.password = hash_password(data.new_password)                                                        # STORE NEW PASSWORD HASH
    consume_verification_token(otp_record)                                                                      # CONSUME ONE-TIME TOKEN
    try:                                                                                                       # START PASSWORD UPDATE
        db.commit()                                                                                             # COMMIT PASSWORD CHANGE
    except Exception:                                                                                           # HANDLE DATABASE FAILURE
        db.rollback()                                                                                           # ROLLBACK PASSWORD CHANGE
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to change password")  # RETURN SAFE ERROR
    return {"message": "Password changed successfully"}                                                       # RETURN SUCCESS


@router.post("/change-email")                                                                                  # CHANGE EMAIL ADDRESS
@limiter.limit("5/minute")                                                                                     # LIMIT SENSITIVE ACCOUNT CHANGES
def change_email(request: Request, data: schemas.ChangeEmailRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):  # APPLY VERIFIED EMAIL CHANGE
    db_user = get_authenticated_user(user, db)                                                                  # LOAD ACTIVE USER
    new_email = data.email.strip().lower()                                                                      # NORMALIZE NEW EMAIL
    if not new_email:                                                                                            # VALIDATE EMAIL
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email address cannot be empty")  # REJECT EMPTY EMAIL
    existing_email = db.query(models.User).filter(models.User.email == new_email).first()                    # CHECK EMAIL UNIQUENESS
    if existing_email and existing_email.id != db_user.id:                                                    # PREVENT EMAIL REUSE
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email address is already registered")  # RETURN DUPLICATE ERROR
    otp_record = get_verified_otp_by_token(db=db, user_id=db_user.id, purpose="change_email", verification_token=data.verification_token)  # FIND VERIFIED EMAIL OTP
    if not otp_record:                                                                                          # VALIDATE VERIFICATION TOKEN
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")    # REJECT INVALID TOKEN
    check_verification_token_expiry(otp_record)                                                                # VALIDATE TOKEN EXPIRATION
    if new_email != otp_record.destination:                                                                     # ENSURE OTP WAS FOR SAME EMAIL
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email address does not match verified OTP destination")  # REJECT MISMATCH
    db_user.email = new_email                                                                                   # UPDATE EMAIL
    db_user.email_verified = True                                                                               # MARK EMAIL VERIFIED
    db_user.is_verified = True                                                                                   # MAINTAIN ACCOUNT VERIFICATION STATE
    consume_verification_token(otp_record)                                                                      # CONSUME ONE-TIME TOKEN
    try:                                                                                                       # START EMAIL UPDATE
        db.commit()                                                                                             # COMMIT EMAIL CHANGE
        db.refresh(db_user)                                                                                    # REFRESH USER
    except Exception:                                                                                           # HANDLE DATABASE FAILURE
        db.rollback()                                                                                           # ROLLBACK EMAIL CHANGE
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to change email address")  # RETURN SAFE ERROR
    return {"message": "Email changed successfully", "email": db_user.email, "email_verified": True}          # RETURN UPDATED EMAIL STATUS


@router.post("/change-username")                                                                               # CHANGE USERNAME
@limiter.limit("5/minute")                                                                                     # LIMIT SENSITIVE ACCOUNT CHANGES
def change_username(request: Request, data: schemas.ChangeUsernameRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):  # APPLY VERIFIED USERNAME CHANGE
    db_user = get_authenticated_user(user, db)                                                                  # LOAD ACTIVE USER
    new_username = data.username.strip()                                                                        # NORMALIZE USERNAME
    if not new_username:                                                                                         # VALIDATE USERNAME
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username cannot be empty")       # REJECT EMPTY USERNAME
    if len(new_username) < 3 or len(new_username) > 50:                                                        # VALIDATE USERNAME LENGTH
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username must be between 3 and 50 characters")  # RETURN LENGTH ERROR
    existing_user = db.query(models.User).filter(models.User.username == new_username).first()                # CHECK USERNAME UNIQUENESS
    if existing_user and existing_user.id != db_user.id:                                                       # PREVENT USERNAME REUSE
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is already taken")       # RETURN DUPLICATE ERROR
    otp_record = get_verified_otp_by_token(db=db, user_id=db_user.id, purpose="change_username", verification_token=data.verification_token)  # FIND VERIFIED USERNAME OTP
    if not otp_record:                                                                                          # VALIDATE VERIFICATION TOKEN
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")    # REJECT INVALID TOKEN
    check_verification_token_expiry(otp_record)                                                                # VALIDATE TOKEN EXPIRATION
    old_username = db_user.username                                                                             # PRESERVE OLD USERNAME
    db_user.username = new_username                                                                              # UPDATE USERNAME
    consume_verification_token(otp_record)                                                                      # CONSUME ONE-TIME TOKEN
    try:                                                                                                       # START USERNAME UPDATE
        db.commit()                                                                                             # COMMIT USERNAME CHANGE
        db.refresh(db_user)                                                                                    # REFRESH USER
    except Exception:                                                                                           # HANDLE DATABASE FAILURE
        db.rollback()                                                                                           # ROLLBACK USERNAME CHANGE
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to change username")  # RETURN SAFE ERROR
    return {"message": "Username changed successfully", "old_username": old_username, "username": db_user.username}  # RETURN UPDATED USERNAME