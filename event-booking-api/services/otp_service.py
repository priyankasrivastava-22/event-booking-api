from datetime import datetime, timedelta, timezone
import secrets

from sqlalchemy.orm import Session

from utils.helpers import generate_otp, hash_otp, verify_otp
from models import OTPVerification


# ============================================================
# CONFIGURATION
# ============================================================

OTP_EXPIRY_MINUTES = 5
VERIFICATION_TOKEN_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 5


ALLOWED_OTP_PURPOSES = {
    "change_username",
    "change_password",
    "change_email",
    "change_phone",
}


# ============================================================
# TIME HELPERS
# ============================================================

def utc_now():
    """
    Return the current UTC time as a timezone-aware datetime.
    """
    return datetime.now(timezone.utc)


def ensure_utc(dt):
    """
    Convert a database datetime into a timezone-aware UTC datetime.

    PostgreSQL/SQLAlchemy may return a naive datetime depending
    on the database column configuration.
    """

    if dt is None:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


# ============================================================
# INVALIDATE PREVIOUS OTP
# ============================================================

def invalidate_previous_otps(
    db: Session,
    user_id: int,
    purpose: str
):
    """
    Invalidate all previous unused OTPs for the same user
    and purpose.

    This guarantees that when a user requests a new OTP:

        old OTP -> invalid
        new OTP -> only valid OTP

    We intentionally invalidate by purpose rather than only
    destination.

    Example:

        change_email -> old email OTP becomes invalid
        change_email -> new email OTP becomes the only valid one
    """

    now = utc_now()

    previous_otps = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.user_id == user_id,
            OTPVerification.purpose == purpose,
            OTPVerification.verified == False
        )
        .all()
    )

    for otp_record in previous_otps:

        otp_record.expires_at = now

        # Remove any verification token that might have existed.
        otp_record.verification_token = None
        otp_record.verification_token_expires_at = None

    db.flush()


# ============================================================
# CREATE OTP
# ============================================================

def create_otp(
    db: Session,
    user_id: int,
    purpose: str,
    destination: str
):
    """
    Generate and store a new OTP.

    Rules:

    - Purpose must be supported.
    - Previous unused OTPs for this purpose are invalidated.
    - OTP is stored as a hash.
    - Raw OTP is returned only to the caller so the caller
      can send it through email/SMS.
    """

    if purpose not in ALLOWED_OTP_PURPOSES:
        raise ValueError("Invalid OTP purpose")

    if not destination:
        raise ValueError("OTP destination is required")

    # --------------------------------------------------------
    # Invalidate previous OTPs
    # --------------------------------------------------------

    invalidate_previous_otps(
        db=db,
        user_id=user_id,
        purpose=purpose
    )

    # --------------------------------------------------------
    # Generate OTP
    # --------------------------------------------------------

    otp = generate_otp()
    otp_hash = hash_otp(otp)

    now = utc_now()

    expires_at = (
        now +
        timedelta(minutes=OTP_EXPIRY_MINUTES)
    )

    # --------------------------------------------------------
    # Create database record
    # --------------------------------------------------------

    otp_record = OTPVerification(
        user_id=user_id,
        purpose=purpose,
        destination=destination,
        otp_hash=otp_hash,
        expires_at=expires_at,
        attempts=0,
        verified=False,
        created_at=now,
        used_at=None,
        verification_token=None,
        verification_token_expires_at=None
    )

    db.add(otp_record)
    db.commit()
    db.refresh(otp_record)

    return otp, otp_record


# ============================================================
# VERIFY OTP
# ============================================================

def verify_otp_code(
    db: Session,
    user_id: int,
    purpose: str,
    otp: str,
    destination: str
):
    """
    Verify an OTP.

    Always returns:

        (success, message, verification_token)

    This keeps the API contract consistent for every failure
    and success path.
    """

    # --------------------------------------------------------
    # Validate purpose
    # --------------------------------------------------------

    if purpose not in ALLOWED_OTP_PURPOSES:
        return (
            False,
            "Invalid OTP purpose",
            None
        )

    # --------------------------------------------------------
    # Validate destination
    # --------------------------------------------------------

    if not destination:
        return (
            False,
            "OTP destination is required",
            None
        )

    # --------------------------------------------------------
    # Find latest active OTP
    # --------------------------------------------------------

    otp_record = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.user_id == user_id,
            OTPVerification.purpose == purpose,
            OTPVerification.destination == destination,
            OTPVerification.verified == False
        )
        .order_by(
            OTPVerification.created_at.desc()
        )
        .first()
    )

    if not otp_record:
        return (
            False,
            "OTP not found or already used",
            None
        )

    # --------------------------------------------------------
    # Current time
    # --------------------------------------------------------

    now = utc_now()

    # --------------------------------------------------------
    # Check OTP expiry
    # --------------------------------------------------------

    expires_at = ensure_utc(
        otp_record.expires_at
    )

    if expires_at is None:
        return (
            False,
            "OTP has no expiry",
            None
        )

    if expires_at <= now:

        # Mark expired OTP as consumed/inactive.
        otp_record.used_at = now
        db.commit()

        return (
            False,
            "OTP has expired",
            None
        )

    # --------------------------------------------------------
    # Check maximum attempts
    # --------------------------------------------------------

    attempts = otp_record.attempts or 0

    if attempts >= MAX_OTP_ATTEMPTS:

        otp_record.used_at = now
        db.commit()

        return (
            False,
            "Maximum OTP attempts exceeded",
            None
        )

    # --------------------------------------------------------
    # Increment attempt BEFORE verification
    # --------------------------------------------------------

    otp_record.attempts = attempts + 1

    # --------------------------------------------------------
    # Verify OTP hash
    # --------------------------------------------------------

    if not verify_otp(
        otp,
        otp_record.otp_hash
    ):

        db.commit()

        remaining_attempts = (
            MAX_OTP_ATTEMPTS -
            otp_record.attempts
        )

        if remaining_attempts <= 0:
            return (
                False,
                "Maximum OTP attempts exceeded",
                None
            )

        return (
            False,
            "Invalid OTP",
            None
        )

    # ========================================================
    # OTP IS CORRECT
    # ========================================================

    otp_record.verified = True
    otp_record.used_at = now

    # --------------------------------------------------------
    # Generate verification token
    # --------------------------------------------------------

    verification_token = secrets.token_urlsafe(32)

    otp_record.verification_token = verification_token

    otp_record.verification_token_expires_at = (
        now +
        timedelta(
            minutes=VERIFICATION_TOKEN_EXPIRY_MINUTES
        )
    )

    db.commit()
    db.refresh(otp_record)

    return (
        True,
        "OTP verified successfully",
        verification_token
    )