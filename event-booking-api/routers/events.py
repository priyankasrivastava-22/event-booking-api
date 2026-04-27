from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas
from utils.helpers import get_db

router = APIRouter()

@router.post("/events", response_model=schemas.EventResponse)
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
        total_seats=event.total_seats,
        available_seats=event.total_seats,

        # BOTH fields
        category=category_name,
        category_id=category_id
    )

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    return db_event


@router.get("/events")
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
        query = query.filter(models.Event.category == category)

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

@router.get("/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404)
    return event


@router.put("/events/{event_id}")
def update_event(event_id: int, data: schemas.EventCreate, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404)

    event.title = data.title
    event.location = data.location
    event.price = data.price
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


@router.delete("/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    db.delete(event)
    db.commit()
    return {"message": "deleted"}