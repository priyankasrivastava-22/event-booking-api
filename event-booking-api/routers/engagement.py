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


@router.delete("/admin/categories/{category_id}")
def delete_category(
    category_id: int,
    db=Depends(get_db),
    user=Depends(get_current_user)
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    category = db.query(models.Category).filter(
        models.Category.id == category_id
    ).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Agar koi event ye category use kar raha hai, usko unlink karo
    db.query(models.Event).filter(
        models.Event.category_id == category_id
    ).update({models.Event.category_id: None})

    db.delete(category)
    db.commit()

    return {"success": True, "message": "Category deleted"}

# ---------------- UPDATE CATEGORY ----------------
@router.put("/admin/categories/{category_id}")
def update_category(
    category_id: int,
    category: CategoryCreate,
    db=Depends(get_db),
    user=Depends(get_current_user)
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    if not category.name.strip():
        raise HTTPException(status_code=400, detail="Category name cannot be empty")

    existing_category = db.query(models.Category).filter(
        models.Category.id == category_id
    ).first()

    if not existing_category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check ki naya naam kisi aur category se clash na kare
    name_conflict = db.query(models.Category).filter(
        models.Category.name == category.name,
        models.Category.id != category_id
    ).first()

    if name_conflict:
        raise HTTPException(status_code=400, detail="Category name already exists")

    old_name = existing_category.name
    existing_category.name = category.name

    # Events jo purana naam (string field) use kar rahe hain, unko bhi update karo
    db.query(models.Event).filter(
        models.Event.category == old_name
    ).update({models.Event.category: category.name})

    db.commit()
    db.refresh(existing_category)

    return existing_category


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

@router.get("/notifications/my")
def get_my_notifications(
    db=Depends(get_db),
    user=Depends(get_current_user)
):
    return db.query(models.Notification).filter(
        (models.Notification.user_name == user["username"]) |
        (models.Notification.user_name.is_(None))
    ).order_by(models.Notification.created_at.desc()).all()
