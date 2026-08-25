from fastapi import Depends, HTTPException, status                                                                  # FASTAPI SECURITY DEPENDENCIES
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials                                               # BEARER TOKEN AUTHENTICATION
from sqlalchemy.orm import Session                                                                                   # SQLALCHEMY SESSION
from jose import jwt, JWTError                                                                                       # JWT ENCODING AND VALIDATION
from passlib.context import CryptContext                                                                             # PASSWORD HASHING
from datetime import datetime, timedelta, timezone                                                                  # UTC TOKEN EXPIRATION
import os                                                                                                            # ENVIRONMENT CONFIGURATION
import hmac                                                                                                          # HMAC GENERATION
import hashlib                                                                                                       # SHA-256 HASHING
import base64                                                                                                        # SAFE HMAC ENCODING
from cryptography.fernet import Fernet, InvalidToken                                                                 # PHONE ENCRYPTION
from database import SessionLocal                                                                                    # DATABASE SESSION FACTORY
import models                                                                                                        # DATABASE MODELS


SECRET_KEY = os.getenv("SECRET_KEY")                                                                                 # JWT SECRET KEY
ALGORITHM = os.getenv("ALGORITHM", "HS256")                                                                         # JWT SIGNING ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))                                   # ACCESS TOKEN LIFETIME
PHONE_ENCRYPTION_KEY = os.getenv("PHONE_ENCRYPTION_KEY")                                                             # FERNET PHONE ENCRYPTION KEY
PHONE_HMAC_SECRET = os.getenv("PHONE_HMAC_SECRET")                                                                   # PHONE LOOKUP HMAC SECRET


if not SECRET_KEY:                                                                                                   # REQUIRE JWT SECRET
    raise RuntimeError("SECRET_KEY not set in environment variables")                                               # FAIL FAST ON MISCONFIGURATION
if not PHONE_ENCRYPTION_KEY:                                                                                          # REQUIRE PHONE ENCRYPTION KEY
    raise RuntimeError("PHONE_ENCRYPTION_KEY not set in environment variables")                                     # FAIL FAST ON MISCONFIGURATION
if not PHONE_HMAC_SECRET:                                                                                             # REQUIRE PHONE HMAC SECRET
    raise RuntimeError("PHONE_HMAC_SECRET not set in environment variables")                                        # FAIL FAST ON MISCONFIGURATION


security = HTTPBearer(auto_error=True)                                                                               # HTTP BEARER AUTHENTICATION
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")                                                    # PASSWORD HASHING CONFIGURATION


try:                                                                                                                 # VALIDATE FERNET CONFIGURATION
    phone_cipher = Fernet(PHONE_ENCRYPTION_KEY.encode())                                                             # INITIALIZE PHONE ENCRYPTION
except Exception as exc:                                                                                             # HANDLE INVALID ENCRYPTION KEY
    raise RuntimeError("PHONE_ENCRYPTION_KEY is invalid. It must be a valid Fernet key.") from exc                   # FAIL FAST ON INVALID KEY


def hash_password(password: str):                                                                                    # PASSWORD HASHING
    if not password:                                                                                                 # VALIDATE PASSWORD INPUT
        raise ValueError("Password cannot be empty")                                                                  # REJECT EMPTY PASSWORD
    return pwd_context.hash(password)                                                                                 # RETURN SECURE PASSWORD HASH


def verify_password(plain: str, hashed: str):                                                                        # PASSWORD VERIFICATION
    if not plain or not hashed:                                                                                       # VALIDATE PASSWORD VALUES
        return False                                                                                                  # FAIL CLOSED FOR INVALID INPUT
    try:                                                                                                              # VERIFY HASH SAFELY
        return pwd_context.verify(plain, hashed)                                                                      # RETURN PASSWORD MATCH RESULT
    except Exception:                                                                                                 # HANDLE INVALID HASH FORMAT
        return False                                                                                                  # FAIL CLOSED


def normalize_phone(phone: str) -> str:                                                                               # PHONE NORMALIZATION
    if not phone:                                                                                                     # REQUIRE PHONE NUMBER
        raise ValueError("Phone number is required")                                                                  # RETURN VALIDATION ERROR
    phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")                        # REMOVE COMMON FORMATTING
    if not phone.startswith("+"):                                                                                     # REQUIRE INTERNATIONAL FORMAT
        raise ValueError("Phone number must include country code")                                                   # RETURN COUNTRY CODE ERROR
    if not phone[1:].isdigit():                                                                                       # VALIDATE NUMERIC PHONE CONTENT
        raise ValueError("Invalid phone number")                                                                      # RETURN PHONE VALIDATION ERROR
    if len(phone) < 8 or len(phone) > 16:                                                                             # ENFORCE E.164-LIKE LENGTH BOUNDARY
        raise ValueError("Invalid phone number length")                                                               # REJECT INVALID PHONE LENGTH
    return phone                                                                                                      # RETURN NORMALIZED PHONE


def encrypt_phone(phone: str) -> str:                                                                                # PHONE ENCRYPTION
    normalized = normalize_phone(phone)                                                                               # NORMALIZE BEFORE ENCRYPTION
    encrypted = phone_cipher.encrypt(normalized.encode("utf-8"))                                                     # ENCRYPT PHONE WITH FERNET
    return encrypted.decode("utf-8")                                                                                  # RETURN DATABASE-SAFE VALUE


def decrypt_phone(encrypted_phone: str) -> str:                                                                      # PHONE DECRYPTION
    if not encrypted_phone:                                                                                           # VALIDATE ENCRYPTED VALUE
        raise ValueError("Encrypted phone number is required")                                                       # RETURN VALIDATION ERROR
    try:                                                                                                              # DECRYPT PHONE SAFELY
        decrypted = phone_cipher.decrypt(encrypted_phone.encode("utf-8"))                                           # DECRYPT FERNET VALUE
        return decrypted.decode("utf-8")                                                                               # RETURN ORIGINAL PHONE
    except (InvalidToken, ValueError, UnicodeDecodeError) as exc:                                                    # HANDLE INVALID ENCRYPTED DATA
        raise ValueError("Unable to decrypt phone number") from exc                                                  # RETURN SAFE ERROR


def phone_lookup_hmac(phone: str) -> str:                                                                            # DETERMINISTIC PHONE LOOKUP HASH
    normalized = normalize_phone(phone)                                                                               # NORMALIZE BEFORE HMAC
    digest = hmac.new(PHONE_HMAC_SECRET.encode("utf-8"), normalized.encode("utf-8"), hashlib.sha256).digest()       # CREATE SHA-256 HMAC
    return base64.urlsafe_b64encode(digest).decode("utf-8")                                                          # RETURN DATABASE-SAFE HMAC


def create_token(data: dict):                                                                                        # CREATE ACCESS TOKEN
    to_encode = data.copy()                                                                                           # COPY PAYLOAD WITHOUT MUTATION
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)                            # CALCULATE TOKEN EXPIRATION
    to_encode.update({"exp": expire})                                                                                 # ADD EXPIRATION CLAIM
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)                                                    # SIGN JWT


def create_token_with_expiry(data: dict, expires_delta: timedelta):                                                  # CREATE CUSTOM-LIFETIME TOKEN
    to_encode = data.copy()                                                                                           # COPY PAYLOAD WITHOUT MUTATION
    expire = datetime.now(timezone.utc) + expires_delta                                                              # CALCULATE CUSTOM EXPIRATION
    to_encode.update({"exp": expire})                                                                                 # ADD EXPIRATION CLAIM
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)                                                    # SIGN JWT


def get_db():                                                                                                        # DATABASE SESSION DEPENDENCY
    db = SessionLocal()                                                                                               # CREATE DATABASE SESSION
    try:                                                                                                              # MANAGE SESSION LIFECYCLE
        yield db                                                                                                      # PROVIDE SESSION TO REQUEST
    finally:                                                                                                          # ALWAYS CLOSE DATABASE SESSION
        db.close()                                                                                                    # RELEASE DATABASE CONNECTION


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):  # AUTHENTICATED USER DEPENDENCY
    token = credentials.credentials                                                                                   # EXTRACT BEARER TOKEN
    blacklisted = db.query(models.BlacklistedToken).filter(models.BlacklistedToken.token == token).first()           # CHECK LOGGED-OUT TOKEN
    if blacklisted:                                                                                                   # REJECT BLACKLISTED TOKEN
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or logged out")          # RETURN AUTHENTICATION ERROR
    try:                                                                                                              # VALIDATE JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])                                              # VERIFY SIGNATURE AND EXPIRATION
        username = payload.get("sub")                                                                                  # EXTRACT USER IDENTITY
        role = payload.get("role")                                                                                     # EXTRACT USER ROLE
        if not username:                                                                                               # REQUIRE SUBJECT CLAIM
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")                    # REJECT INVALID TOKEN
        db_user = db.query(models.User).filter(models.User.username == username).first()                             # LOAD CURRENT USER
        if not db_user:                                                                                                # VALIDATE USER EXISTENCE
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")                  # REJECT DELETED USER TOKEN
        if not db_user.is_active:                                                                                      # VALIDATE ACCOUNT STATUS
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")            # REJECT DISABLED ACCOUNT
        return {"username": db_user.username, "role": db_user.role}                                                   # RETURN CURRENT AUTHORITATIVE USER DATA
    except HTTPException:                                                                                              # PRESERVE EXPECTED AUTH ERRORS
        raise                                                                                                         # RE-RAISE HTTP ERROR
    except JWTError:                                                                                                  # HANDLE INVALID OR EXPIRED JWT
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")                       # RETURN SAFE AUTH ERROR


def get_user_by_username(db: Session, username: str):                                                               # USERNAME LOOKUP HELPER
    return db.query(models.User).filter(models.User.username == username).first()                                   # RETURN MATCHING USER


def get_user_by_phone_hmac(db: Session, phone: str):                                                                 # PHONE LOOKUP HELPER
    lookup_hash = phone_lookup_hmac(phone)                                                                            # GENERATE DETERMINISTIC PHONE HMAC
    return db.query(models.User).filter(models.User.phone_lookup_hmac == lookup_hash).first()                       # RETURN MATCHING USER