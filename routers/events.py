from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas
from utils.helpers import get_db

router = APIRouter()

@router.post("/events", response_model=schemas.EventResponse)
def create_event(event: schemas.EventCreate, db: Session = Depends(get_db)):
    db_event = models.Event(**event.dict(), available_seats=event.total_seats)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


@router.get("/events")
def get_events(page: int = 1, limit: int = 10, db: Session = Depends(get_db)):
    skip = (page - 1) * limit
    return db.query(models.Event).offset(skip).limit(limit).all()


@router.get("/events/search")
def search_events(title: str = None, category: str = None, db: Session = Depends(get_db)):
    query = db.query(models.Event)

    if title:
        query = query.filter(models.Event.title.contains(title))
    if category:
        query = query.filter(models.Event.category == category)

    return query.all()


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
    event.category = data.category

    db.commit()
    return event


@router.delete("/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    db.delete(event)
    db.commit()
    return {"message": "deleted"}