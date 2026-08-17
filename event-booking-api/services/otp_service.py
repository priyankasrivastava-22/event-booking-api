from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from utils.helpers import generate_otp, hash_otp, verify_otp
from models import OTPVerification


OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 5


ALLOWED_OTP_PURPOSES = {
    "change_username",
    "change_password",
    "change_email",
    "change_phone",
}

def create_otp(
    db: Session,
    user_id: int,
    purpose: str,
    destination: str
):
    if purpose not in ALLOWED_OTP_PURPOSES:
        raise ValueError("Invalid OTP purpose")

    otp = generate_otp()
    otp_hash = hash_otp(otp)

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=OTP_EXPIRY_MINUTES
    )

    otp_record = OTPVerification(
        user_id=user_id,
        purpose=purpose,
        destination=destination,
        otp_hash=otp_hash,
        expires_at=expires_at,
        attempts=0,
        verified=False
    )

    db.add(otp_record)
    db.commit()
    db.refresh(otp_record)

    return otp, otp_record

def verify_otp_code(
    db: Session,
    user_id: int,
    purpose: str,
    otp: str,
    destination: str
):
    otp_record = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.user_id == user_id,
            OTPVerification.purpose == purpose,
            OTPVerification.destination == destination,
            OTPVerification.verified.is_(False)
        )
        .order_by(OTPVerification.created_at.desc())
        .first()
    )

    if not otp_record:
        return False, "OTP not found or already used"

    now = datetime.now(timezone.utc)

    if otp_record.expires_at < now:
        return False, "OTP has expired"

    if otp_record.attempts >= MAX_OTP_ATTEMPTS:
        return False, "Maximum OTP attempts exceeded"

    otp_record.attempts += 1

    if not verify_otp(otp, otp_record.otp_hash):
        db.commit()
        return False, "Invalid OTP"

    otp_record.verified = True
    otp_record.used_at = now

    db.commit()

    return True, "OTP verified successfully"