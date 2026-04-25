from fastapi import APIRouter, Depends, HTTPException, Request
from core.limiter import limiter
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt

import models, schemas

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
def register(
    request: Request,
    user: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    existing = db.query(models.User).filter(
        models.User.username == user.username
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = models.User(
        username=user.username,
        password=hash_password(user.password),  # password hashed correctly
        role=user.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ---------------- LOGIN ----------------
# FIX: use separate schema for login (only username + password)
class LoginRequest(schemas.BaseModel):
    username: str
    password: str


@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    user: LoginRequest,
    db: Session = Depends(get_db)
):
    db_user = db.query(models.User).filter(
        models.User.username == user.username
    ).first()

    # unified error (better security + avoids confusion)
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # FIX: correct password verification
    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not db_user.is_active:
        raise HTTPException(status_code=403, detail="User blocked")

    token = create_token({
        "sub": db_user.username,
        "role": db_user.role
    })

    return {"access_token": token, "token_type": "bearer"}


# ---------------- LOGOUT ----------------
@router.post("/logout")
def logout(token: str, db: Session = Depends(get_db)):

    db.add(models.BlacklistedToken(token=token))
    db.commit()

    return {"message": "Logged out"}


# ---------------- PASSWORD RESET REQUEST ----------------
@router.post("/password-reset/request")
def request_reset(username: str, db: Session = Depends(get_db)):

    user = db.query(models.User).filter(
        models.User.username == username
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = create_token({"sub": username})

    record = models.PasswordReset(
        username=username,
        token=token,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )

    db.add(record)
    db.commit()

    return {"reset_token": token}


# ---------------- PASSWORD RESET CONFIRM ----------------
@router.post("/password-reset/confirm")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):

    record = db.query(models.PasswordReset).filter(
        models.PasswordReset.token == token
    ).first()

    if not record:
        raise HTTPException(status_code=400, detail="Invalid token")

    if record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expired")

    user = db.query(models.User).filter(
        models.User.username == record.username
    ).first()

    user.password = hash_password(new_password)

    db.delete(record)
    db.commit()

    return {"message": "Password updated"}


# ---------------- VERIFY REQUEST ----------------
@router.post("/verify/request")
def send_verification(username: str, db: Session = Depends(get_db)):

    user = db.query(models.User).filter(
        models.User.username == username
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = create_token({"sub": username})

    db.add(models.EmailVerification(username=username, token=token))
    db.commit()

    return {"verification_token": token}


# ---------------- VERIFY CONFIRM ----------------
@router.post("/verify/confirm")
def verify_account(token: str, db: Session = Depends(get_db)):

    data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = data.get("sub")

    user = db.query(models.User).filter(
        models.User.username == username
    ).first()

    user.is_verified = True
    db.commit()

    return {"message": "Account verified"}