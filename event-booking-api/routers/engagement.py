from fastapi import APIRouter, Depends, HTTPException
import models
from utils.helpers import get_db
from core.security import get_current_user
from schemas import CategoryCreate, NotificationCreate

router = APIRouter()

@router.get("/categories")                                                                                               # CATEGORIES
def get_categories( db=Depends(get_db)):
    return db.query(models.Category).all()

@router.post("/admin/categories")                                                                                        # CREATE CATEGORY
def create_category( category: CategoryCreate, db=Depends(get_db), user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException( status_code=403, detail="Only admin allowed")
    category_name = category.name.strip()
    if not category_name:
        raise HTTPException( status_code=400, detail="Category name cannot be empty")
    existing = db.query(models.Category).filter(models.Category.name == category_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category exists")
    new_category = models.Category( name=category_name )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

@router.delete("/admin/categories/{category_id}")                                                                        # DELETE CATEGORY
def delete_category( category_id: int, db=Depends(get_db),user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException( status_code=403, detail="Only admin allowed")
    category = db.query(models.Category).filter( models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    db.query(models.Event).filter(models.Event.category_id == category_id).update(                                       # Unlink events using this category
        {
            models.Event.category_id: None
        },
        synchronize_session=False
    )
    db.delete(category)
    db.commit()
    return {
        "success": True,
        "message": "Category deleted"
    }

@router.put("/admin/categories/{category_id}")                                                                           # UPDATE CATEGORY
def update_category( category_id: int, category: CategoryCreate, db=Depends(get_db), user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException( status_code=403, detail="Only admin allowed")
    category_name = category.name.strip()
    if not category_name:
        raise HTTPException( status_code=400, detail="Category name cannot be empty")
    existing_category = db.query(models.Category).filter( models.Category.id == category_id).first()
    if not existing_category:
        raise HTTPException( status_code=404,detail="Category not found")
    name_conflict = db.query(models.Category).filter( models.Category.name == category_name, models.Category.id != category_id).first()
    if name_conflict:
        raise HTTPException( status_code=400, detail="Category name already exists")
    old_name = existing_category.name
    existing_category.name = category_name

    # Temporary compatibility with existing Event.category field.
    # category_id remains the actual relationship.
    db.query(models.Event).filter( models.Event.category == old_name).update(
        {
            models.Event.category: category_name
        },
        synchronize_session=False
    )
    db.commit()
    db.refresh(existing_category)
    return existing_category

@router.post("/admin/notify")                                                                                            # ADMIN SEND NOTIFICATION
def notify( data: NotificationCreate, db=Depends(get_db), user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException( status_code=403, detail="Only admin allowed")
    target_user_id = None
    # Personal notification. Existing frontend can still send user_name. resolve it to user_id before storing.
    if data.user_name:
        target_user = db.query(models.User).filter( models.User.username == data.user_name).first()
        if not target_user:
            raise HTTPException( status_code=404, detail="Target user not found")
        target_user_id = target_user.id
    # Create notification. user_id = NULL means broadcast notification.
    notification = models.Notification( message=data.message, user_id=target_user_id)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return {
        "success": True,
        "message": "Notification sent"
    }

@router.get("/notifications/my")                                                                                         # MY NOTIFICATIONS
def get_my_notifications( db=Depends(get_db), user=Depends(get_current_user)):
    db_user = db.query(models.User).filter( models.User.username == user["username"]).first()
    if not db_user:
        raise HTTPException( status_code=404, detail="User not found")
    notifications = db.query(models.Notification).filter(
        (models.Notification.user_id == db_user.id) |
        (models.Notification.user_id.is_(None))
    ).order_by(
        models.Notification.created_at.desc()
    ).all()
    return notifications