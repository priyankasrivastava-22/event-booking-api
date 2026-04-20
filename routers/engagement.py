from fastapi import APIRouter, Depends, HTTPException
import models
from core.security import get_db, get_current_user
from schemas import CategoryCreate, NotificationCreate

router = APIRouter()

# ---------------- CATEGORIES ----------------
@router.get("/categories")
def get_categories(db=Depends(get_db)):
    categories = db.query(models.Category).all()
    return categories


@router.post("/admin/categories")
def create_category(
    category: CategoryCreate,
    db=Depends(get_db),
    user=Depends(get_current_user)
):
    if not category.name.strip():
        raise HTTPException(status_code=400, detail="Category name cannot be empty")

    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    existing = db.query(models.Category).filter(
        models.Category.name == category.name
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Category exists")

    new_category = models.Category(name=category.name)
    db.add(new_category)
    db.commit()
    db.refresh(new_category)

    return new_category


# ---------------- NOTIFICATIONS ----------------
@router.post("/admin/notify")
def notify(
    data: NotificationCreate,
    db=Depends(get_db),
    user=Depends(get_current_user)
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    db.add(models.Notification(
        message=data.message,
        user_name=data.user_name  #supports both broadcast & personal
    ))

    db.commit()

    return {"success": True, "message": "Notification sent"}

@router.get("/my-notifications")
def get_my_notifications(
    db=Depends(get_db),
    user=Depends(get_current_user)
):
    return db.query(models.Notification).filter(
        (models.Notification.user_name == user["username"]) |
        (models.Notification.user_name.is_(None))
    ).order_by(models.Notification.created_at.desc()).all()