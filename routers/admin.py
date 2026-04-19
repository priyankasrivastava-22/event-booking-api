from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas
from utils.helpers import get_db

router = APIRouter(prefix="/admin", tags=["Admin"])


def admin_check(user):
    if user["role"] != "admin":
        raise HTTPException(status_code=403)


@router.get("/users")
def users(db: Session = Depends(get_db)):
    return db.query(models.User).all()


@router.get("/bookings")
def bookings(db: Session = Depends(get_db)):
    return db.query(models.Booking).all()