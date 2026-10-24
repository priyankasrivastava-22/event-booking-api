from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import cloudinary.uploader
from core.cloudinary_config import cloudinary
import models
from core.security import get_db, get_current_user

# Router instance
router = APIRouter()

# VIEW PROFILE
@router.get("/")
def get_profile(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Fetch logged-in user's profile details
    """

    db_user = db.query(models.User).filter(
        models.User.username == user["username"]
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "username": db_user.username,
        "role": db_user.role,
        "full_name": getattr(db_user, "full_name", None),
        "bio": getattr(db_user, "bio", None),
        "profile_image": getattr(db_user, "profile_image", None)
    }


# UPDATE PROFILE
@router.put("/")
def update_profile(
    data: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Update user profile fields (safe partial updates)
    """

    db_user = db.query(models.User).filter(
        models.User.username == user["username"]
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update only provided fields
    if data.get("full_name") is not None:
        db_user.full_name = data["full_name"]

    if data.get("bio") is not None:
        db_user.bio = data["bio"]

    if data.get("email") is not None:
        raise HTTPException(status_code=400, detail="Change your email using the verified OTP flow in Account Settings")

    db.commit()
    db.refresh(db_user)

    return {"message": "Profile updated"}

# UPLOAD PROFILE IMAGE
@router.post("/upload-image")
def upload_profile_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    db_user = db.query(models.User).filter(
        models.User.username == user["username"]
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    result = cloudinary.uploader.upload(
        file.file,
        folder="profile_images",
        public_id=f"user_{user['username']}",
        overwrite=True,
        transformation=[{
            "width": 200,
            "height": 200,
            "crop": "fill",
            "gravity": "face"
        }]
    )

    db_user.profile_image = result["secure_url"]
    db.commit()
    db.refresh(db_user)

    return {
        "message": "Image uploaded",
        "image_url": result["secure_url"]
    }

# DELETE ACCOUNT
@router.delete("/")
def delete_account(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Permanently delete user account
    """

    db_user = db.query(models.User).filter(
        models.User.username == user["username"]
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Preserve paid tickets, payment receipts and audit history. Deactivate instead.
    # A separately approved retention/deletion workflow may later anonymize account data.
    db_user.is_active = False
    db.commit()
    return {"message": "Account deactivated. Existing orders remain on record."}