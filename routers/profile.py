"""from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import shutil
import os

import models
from core.security import get_db, get_current_user

router = APIRouter()

UPLOAD_DIR = "uploads/profiles"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- VIEW PROFILE ----------------
@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

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


# ---------------- UPDATE PROFILE ----------------
@router.put("/profile")
def update_profile(
    data: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    db_user = db.query(models.User).filter(
        models.User.username == user["username"]
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # SAFE FIELD UPDATES (no schema break)
    if data.get("full_name") is not None:
        db_user.full_name = data["full_name"]

    if data.get("bio") is not None:
        db_user.bio = data["bio"]

    if data.get("email") is not None:
        db_user.email = data["email"]

    db.commit()
    db.refresh(db_user)

    return {"message": "Profile updated"}


# ---------------- UPLOAD PROFILE IMAGE ----------------
@router.post("/profile/upload-image")
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

    file_path = f"{UPLOAD_DIR}/{user['username']}_{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    db_user.profile_image = file_path
    db.commit()
    db.refresh(db_user)

    return {"message": "Image uploaded", "path": file_path}


# ---------------- DELETE ACCOUNT ----------------
@router.delete("/profile")
def delete_account(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    db_user = db.query(models.User).filter(
        models.User.username == user["username"]
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()

    return {"message": "Account deleted"}"""


from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import shutil
import os

import models
from core.security import get_db, get_current_user

# Router instance
router = APIRouter()

# Directory for storing profile images
UPLOAD_DIR = "uploads/profiles"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# VIEW PROFILE
@router.get("/profile")
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
@router.put("/profile")
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
        db_user.email = data["email"]

    db.commit()
    db.refresh(db_user)

    return {"message": "Profile updated"}

# UPLOAD PROFILE IMAGE
@router.post("/profile/upload-image")
def upload_profile_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Upload and store user profile image locally
    """

    db_user = db.query(models.User).filter(
        models.User.username == user["username"]
    ).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Save file with username prefix to avoid collision
    file_path = f"{UPLOAD_DIR}/{user['username']}_{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    db_user.profile_image = file_path
    db.commit()
    db.refresh(db_user)

    return {
        "message": "Image uploaded",
        "path": file_path
    }


# DELETE ACCOUNT
@router.delete("/profile")
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

    db.delete(db_user)
    db.commit()

    return {"message": "Account deleted"}