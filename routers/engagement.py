from fastapi import APIRouter, Depends, HTTPException
import models
from core.security import get_db, get_current_user

router = APIRouter()

# ---------------- CATEGORIES ----------------
@router.get("/categories")
def get_categories(db=Depends(get_db)):
    return db.query(models.Category).all()


@router.post("/admin/categories")
def create_category(name: str, db=Depends(get_db), user=Depends(get_current_user)):

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    existing = db.query(models.Category).filter(models.Category.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category exists")

    db.add(models.Category(name=name))
    db.commit()
    return {"message": "Category created"}


# ---------------- NOTIFICATIONS ----------------
@router.post("/admin/notify")
def notify(message: str, db=Depends(get_db), user=Depends(get_current_user)):

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    db.add(models.Notification(message=message))
    db.commit()

    return {"message": "Notification sent"}