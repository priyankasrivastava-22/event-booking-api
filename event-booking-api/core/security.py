# """from fastapi import Depends, HTTPException
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from sqlalchemy.orm import Session
# from jose import jwt, JWTError
# from passlib.context import CryptContext
# from datetime import datetime, timedelta
# import os
#
# from database import SessionLocal
# import models
#
# # ENV
# SECRET_KEY = os.getenv("SECRET_KEY")
# ALGORITHM = os.getenv("ALGORITHM", "HS256")
# ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
#
# # SAFETY CHECK (kept as-is, but safer message)
# if not SECRET_KEY:
#     raise Exception("SECRET_KEY not set in environment variables")
#
# # Security
# security = HTTPBearer()
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
#
# # ---------------- PASSWORD ----------------
# def hash_password(password: str):
#     return pwd_context.hash(password)
#
# def verify_password(plain, hashed):
#     return pwd_context.verify(plain, hashed)
#
# # ---------------- JWT ----------------
# def create_token(data: dict):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     to_encode.update({"exp": expire})
#
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#
#
# # 🔥 ADDED: Extended token creation (USED FOR EMAIL VERIFICATION / RESET)
# # (Does NOT affect old create_token usage)
# def create_token_with_expiry(data: dict, expires_delta: timedelta):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + expires_delta
#     to_encode.update({"exp": expire})
#
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#
#
# # ---------------- DB ----------------
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
#
#
# # ---------------- CURRENT USER ----------------
# def get_current_user(
#     credentials: HTTPAuthorizationCredentials = Depends(security),
#     db: Session = Depends(get_db)
# ):
#     token = credentials.credentials
#
#     blacklisted = db.query(models.BlacklistedToken).filter(
#         models.BlacklistedToken.token == token
#     ).first()
#
#     if blacklisted:
#         raise HTTPException(status_code=401, detail="Token expired or logged out")
#
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username = payload.get("sub")
#         role = payload.get("role")
#
#         if not username:
#             raise HTTPException(status_code=401, detail="Invalid token")
#
#         return {"username": username, "role": role}
#
#     except JWTError:
#         raise HTTPException(status_code=401, detail="Invalid token")
#
#
# # ADDED: Helper for verification/password reset flows
# # (safe DB helper reuse in auth module)
# def get_user_by_username(db: Session, username: str):
#     return db.query(models.User).filter(models.User.username == username).first()"""
#
#
# from fastapi import Depends, HTTPException
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from sqlalchemy.orm import Session
# from jose import jwt, JWTError
# from passlib.context import CryptContext
# from datetime import datetime, timedelta, timezone
# import os
# from database import SessionLocal
# import models
#
# # ENV
# SECRET_KEY = os.getenv("SECRET_KEY")
# ALGORITHM = os.getenv("ALGORITHM", "HS256")
# ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
#
# # IMPORTANT: prevent crash but still enforce requirement
# if not SECRET_KEY:
#     raise RuntimeError("SECRET_KEY not set in environment variables (.env missing or not loaded)")
#
# # Security
# security = HTTPBearer()
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
#
# # ---------------- PASSWORD ----------------
# def hash_password(password: str):
#     return pwd_context.hash(password)
#
# def verify_password(plain, hashed):
#     return pwd_context.verify(plain, hashed)
#
# # ---------------- JWT ----------------
# def create_token(data: dict):
#     to_encode = data.copy()
#     expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     to_encode.update({"exp": expire})
#
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#
# # ---------------- DB ----------------
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
#
# # ---------------- CURRENT USER ----------------
# def get_current_user(
#     credentials: HTTPAuthorizationCredentials = Depends(security),
#     db: Session = Depends(get_db)
# ):
#     token = credentials.credentials
#
#     # check blacklist
#     blacklisted = db.query(models.BlacklistedToken).filter(
#         models.BlacklistedToken.token == token
#     ).first()
#
#     if blacklisted:
#         raise HTTPException(status_code=401, detail="Token expired or logged out")
#
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username = payload.get("sub")
#         role = payload.get("role")
#
#         if not username:
#             raise HTTPException(status_code=401, detail="Invalid token")
#
#         return {
#             "username": username,
#             "role": role
#         }
#
#     except JWTError:
#         raise HTTPException(status_code=401, detail="Invalid token")

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import os
import hmac
import hashlib
import base64

from cryptography.fernet import Fernet, InvalidToken

from database import SessionLocal
import models


# ============================================================
# ENVIRONMENT
# ============================================================

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

PHONE_ENCRYPTION_KEY = os.getenv("PHONE_ENCRYPTION_KEY")
PHONE_HMAC_SECRET = os.getenv("PHONE_HMAC_SECRET")


# ============================================================
# SAFETY CHECKS
# ============================================================

if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY not set in environment variables"
    )

if not PHONE_ENCRYPTION_KEY:
    raise RuntimeError(
        "PHONE_ENCRYPTION_KEY not set in environment variables"
    )

if not PHONE_HMAC_SECRET:
    raise RuntimeError(
        "PHONE_HMAC_SECRET not set in environment variables"
    )


# ============================================================
# SECURITY
# ============================================================

security = HTTPBearer()

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

try:
    phone_cipher = Fernet(PHONE_ENCRYPTION_KEY.encode())
except Exception as exc:
    raise RuntimeError(
        "PHONE_ENCRYPTION_KEY is invalid. "
        "It must be a valid Fernet key."
    ) from exc


# ============================================================
# PASSWORD
# ============================================================

def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)


# ============================================================
# PHONE NORMALIZATION
# ============================================================

def normalize_phone(phone: str) -> str:
    """
    Normalize a phone number into a consistent format.

    For Eventora, phone numbers should ultimately be stored
    in E.164 format, for example:

        +919876543210

    Full country-aware validation will be handled by the auth
    layer using a proper phone-number library.
    """

    if not phone:
        raise ValueError("Phone number is required")

    phone = phone.strip()

    # Remove common formatting characters.
    phone = (
        phone
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    if not phone.startswith("+"):
        raise ValueError(
            "Phone number must include country code"
        )

    if not phone[1:].isdigit():
        raise ValueError(
            "Invalid phone number"
        )

    return phone


# ============================================================
# PHONE ENCRYPTION
# ============================================================

def encrypt_phone(phone: str) -> str:
    """
    Encrypt a normalized phone number.

    Encryption is randomized, so the encrypted value should
    NOT be used for database lookup.
    """

    normalized = normalize_phone(phone)

    encrypted = phone_cipher.encrypt(
        normalized.encode("utf-8")
    )

    return encrypted.decode("utf-8")


def decrypt_phone(encrypted_phone: str) -> str:
    """
    Decrypt an encrypted phone number.
    """

    try:
        decrypted = phone_cipher.decrypt(
            encrypted_phone.encode("utf-8")
        )

        return decrypted.decode("utf-8")

    except InvalidToken:
        raise ValueError(
            "Unable to decrypt phone number"
        )


# ============================================================
# PHONE HMAC
# ============================================================

def phone_lookup_hmac(phone: str) -> str:
    """
    Generate a deterministic HMAC for phone lookup.

    This value is safe to use for:

        - uniqueness checks
        - finding a user by phone
        - phone-based login lookup

    The raw phone number is never stored as the lookup value.
    """

    normalized = normalize_phone(phone)

    digest = hmac.new(
        PHONE_HMAC_SECRET.encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256
    ).digest()

    return base64.urlsafe_b64encode(
        digest
    ).decode("utf-8")


# ============================================================
# JWT
# ============================================================

def create_token(data: dict):
    """
    Create the normal Eventora access token.
    """

    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc)
        + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def create_token_with_expiry(
    data: dict,
    expires_delta: timedelta
):
    """
    Create a JWT with a custom expiration time.

    Used by verification/reset flows that need a different
    lifetime from the normal access token.
    """

    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc)
        + expires_delta
    )

    to_encode.update({
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# ============================================================
# DATABASE
# ============================================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================
# CURRENT USER
# ============================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    # --------------------------------------------------------
    # BLACKLIST CHECK
    # --------------------------------------------------------

    blacklisted = (
        db.query(models.BlacklistedToken)
        .filter(
            models.BlacklistedToken.token == token
        )
        .first()
    )

    if blacklisted:
        raise HTTPException(
            status_code=401,
            detail="Token expired or logged out"
        )

    # --------------------------------------------------------
    # JWT VALIDATION
    # --------------------------------------------------------

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")
        role = payload.get("role")

        if not username:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        return {
            "username": username,
            "role": role
        }

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )


# ============================================================
# USER LOOKUP
# ============================================================

def get_user_by_username(
    db: Session,
    username: str
):
    return (
        db.query(models.User)
        .filter(
            models.User.username == username
        )
        .first()
    )


def get_user_by_phone_hmac(
    db: Session,
    phone: str
):
    """
    Find a user using the deterministic HMAC of the
    normalized phone number.
    """

    lookup_hash = phone_lookup_hmac(phone)

    return (
        db.query(models.User)
        .filter(
            models.User.phone_lookup_hmac == lookup_hash
        )
        .first()
    )