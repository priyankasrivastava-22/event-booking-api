from fastapi import APIRouter, Depends, HTTPException, Request
from core.limiter import limiter
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt
from pydantic import BaseModel

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
        role=user.role
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

    # ---------------- FIND USER (username OR email) ----------------
    db_user = db.query(models.User).filter(
        (models.User.username == user.username) |
        (models.User.email == user.username)
    ).first()

    # ---------------- USER NOT FOUND ----------------
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # ---------------- PASSWORD SAFETY CHECK ----------------
    if not db_user.password:
        raise HTTPException(status_code=400, detail="Corrupted user data")

    # ---------------- VERIFY PASSWORD ----------------
    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # ---------------- USER STATUS CHECK (optional safety) ----------------
    if hasattr(db_user, "is_active") and not db_user.is_active:
        raise HTTPException(status_code=403, detail="User blocked")

    # ---------------- CREATE TOKEN ----------------
    token = create_token({
        "sub": db_user.username,
        "role": db_user.role
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }


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


# ---------------- DEBUG ----------------
@router.get("/debug-db")
def debug_db(db: Session = Depends(get_db)):
    return {
        "users": db.query(models.User).count(),
        "events": db.query(models.Event).count(),
        "bookings": db.query(models.Booking).count()
    }


@router.get("/all-bookings")
def all_bookings(db: Session = Depends(get_db)):
    return db.query(models.Booking).all()

@router.get("/debug-user/{username}")
def debug(username: str, db: Session = Depends(get_db)):
    return db.query(models.User).filter(models.User.username == username).first()

@router.get("/reset-db")
def reset(db: Session = Depends(get_db)):
    db.query(models.User).delete()
    db.commit()
    return {"message": "DB cleared"}

