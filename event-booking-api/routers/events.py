from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import cloudinary.uploader
from core.cloudinary_config import cloudinary
from sqlalchemy.orm import Session
import models, schemas
from utils.helpers import get_db

router = APIRouter()

@router.post("/", response_model=schemas.EventResponse)
def create_event(event: schemas.EventCreate, db: Session = Depends(get_db)):

    category_id = None
    category_name = None

    # NEW SYSTEM
    if event.category_id:
        category = db.query(models.Category).filter(
            models.Category.id == event.category_id
        ).first()

        if not category:
            raise HTTPException(status_code=400, detail="Invalid category_id")

        category_id = category.id
        category_name = category.name

    # OLD SYSTEM (fallback)
    elif event.category:
        category_name = event.category

    db_event = models.Event(
        title=event.title,
        location=event.location,
        description=event.description,
        date_time=event.date_time,
        price=event.price,
        image_url=event.image_url,
        total_seats=event.total_seats,
        available_seats=event.total_seats,
        category=category_name,
        category_id=category_id
    )

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    return db_event


@router.get("/")
def get_events(
    page: int = 1,
    limit: int = 16,

    # SEARCH
    title: str = None,

    # FILTERS
    category: str = None,
    date: str = None,
    min_price: int = None,
    max_price: int = None,

    db: Session = Depends(get_db)
):
    query = db.query(models.Event)

    # SEARCH BY TITLE
    if title:
        query = query.filter(models.Event.title.ilike(f"%{title}%"))

    # FILTER BY CATEGORY (NEW)
    if category:
        query = query.filter(models.Event.category.ilike(category))

    # FILTER BY DATE
    if date:
        query = query.filter(models.Event.date_time == date)

    # FILTER BY PRICE
    if min_price is not None:
        query = query.filter(models.Event.price >= min_price)

    if max_price is not None:
        query = query.filter(models.Event.price <= max_price)

    # PAGINATION
    skip = (page - 1) * limit
    events = query.offset(skip).limit(limit).all()

    return events

@router.get("/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404)
    return event


@router.put("/{event_id}")
def update_event(event_id: int, data: schemas.EventUpdate, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404)

    event.title = data.title
    event.location = data.location
    event.price = data.price
    event.image_url = data.image_url
    # handle category update safely
    if data.category_id:
        category = db.query(models.Category).filter(
            models.Category.id == data.category_id
        ).first()

        if not category:
            raise HTTPException(status_code=400, detail="Invalid category_id")

        event.category_id = category.id
        event.category = category.name

    elif data.category:
        event.category = data.category

    db.commit()
    return event


@router.delete("/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    db.delete(event)
    db.commit()
    return {"message": "deleted"}


# ---------------- UPLOAD EVENT IMAGE ----------------
@router.post("/{event_id}/upload-image")
def upload_event_image(
    event_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    result = cloudinary.uploader.upload(
        file.file,
        folder="event_images",
        transformation=[{"width": 1200, "height": 675, "crop": "fill"}]
    )

    event.image_url = result["secure_url"]
    db.commit()
    db.refresh(event)

    return {"message": "Image uploaded", "image_url": event.image_url}