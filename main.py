"""from passlib.context import CryptContext
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import models
from database import engine, SessionLocal
import schemas
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Header
from dotenv import load_dotenv
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

load_dotenv()

def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token missing")

    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth header")

        token = parts[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")

        return username

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

app = FastAPI()

# Create tables
models.Base.metadata.create_all(bind=engine)

# Dependency (DB connection)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check duplicate user
    existing = db.query(models.User).filter(models.User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Hash password
    hashed = hash_password(user.password)

    new_user = models.User(
        username=user.username,
        password=hashed
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    print("Registering user:", user.username)
    return new_user

#SECRET_KEY = os.getenv("SECRET_KEY")
#ALGORITHM = os.getenv("ALGORITHM")
#ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

SECRET_KEY = os.getenv("SECRET_KEY", "devsecret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@app.post("/login")
def login(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Wrong password")

    token = create_token({"sub": user.username})

    return {"access_token": token}

@app.get("/")
def home():
    return {"message": "Event Booking API is running"}

@app.post("/events", response_model=schemas.EventResponse)
def create_event(event: schemas.EventCreate, db: Session = Depends(get_db)):
    db_event = models.Event(
        title=event.title,
        location=event.location,
        total_seats=event.total_seats,
        available_seats=event.total_seats
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    return db_event

@app.get("/events", response_model=list[schemas.EventResponse])
def get_events(db: Session = Depends(get_db)):
    return db.query(models.Event).all()


@app.get("/events/{event_id}", response_model=schemas.EventResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return event

@app.put("/events/{event_id}", response_model=schemas.EventResponse)
def update_event(event_id: int, updated_event: schemas.EventCreate, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event.title = updated_event.title
    event.location = updated_event.location
    event.total_seats = updated_event.total_seats

    db.commit()
    db.refresh(event)

    return event

@app.delete("/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db.delete(event)
    db.commit()

    return {"message": "Event deleted"}


@app.post("/book", response_model=schemas.BookingResponse)
def book_event(
    booking: schemas.BookingCreate,
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    print("Authorization Header:", authorization)
    if not authorization:
        raise HTTPException(status_code=401, detail="Token missing")

    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth header")

        token = parts[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if not username:
             raise HTTPException(status_code=401, detail="Invalid token")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 1. Check event exists
    event = db.query(models.Event).filter(models.Event.id == booking.event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # 2. Check seats
    if event.available_seats < booking.tickets:
        raise HTTPException(status_code=400, detail="Not enough seats available")

    # 3. Reduce seats
    event.available_seats -= booking.tickets

    # 4. Create booking (IMPORTANT: use username from token)
    new_booking = models.Booking(
        user_name=username,
        event_id=booking.event_id,
        tickets=booking.tickets
    )

    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    return new_booking


@app.get("/my-bookings", response_model=list[schemas.BookingResponse])
def get_my_bookings(
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    bookings = db.query(models.Booking).filter(models.Booking.user_name == username).all()
    return bookings


@app.delete("/book/{booking_id}")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # 🔒 Check ownership
    if booking.user_name != username:
        raise HTTPException(status_code=403, detail="Not allowed")

    event = db.query(models.Event).filter(models.Event.id == booking.event_id).first()

    if event:
        event.available_seats += booking.tickets

    db.delete(booking)
    db.commit()

    return {"message": "Booking cancelled"}


"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

import models
import schemas
from database import engine, SessionLocal

# Initialize FastAPI app
app = FastAPI()

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Load environment variables
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

if not SECRET_KEY:
    raise Exception("SECRET_KEY not set in .env")

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# JWT token creation
def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Security setup
security = HTTPBearer()

# Get current user from token
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")

        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {"username": username, "role": role}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Home route
@app.get("/")
def home():
    return {"message": "Event Booking API is running"}

# Register user
@app.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == user.username).first()

    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = hash_password(user.password)

    new_user = models.User(
        username=user.username,
        password=hashed_password,
        role=user.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

# Login user
@app.post("/login")
def login(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Wrong password")

    token = create_token({
        "sub": db_user.username,
        "role": db_user.role
    })

    return {"access_token": token}

# Create event
@app.post("/events", response_model=schemas.EventResponse)
def create_event(event: schemas.EventCreate, db: Session = Depends(get_db)):
    db_event = models.Event(
        title=event.title,
        location=event.location,
        total_seats=event.total_seats,
        available_seats=event.total_seats,
        description = event.description,
        date_time = event.date_time,
        price = event.price,
        category = event.category
    )

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    return db_event

# Get all events
@app.get("/events", response_model=list[schemas.EventResponse])
def get_events(db: Session = Depends(get_db)):
    return db.query(models.Event).all()

# Get single event
@app.get("/events/{event_id}", response_model=schemas.EventResponse)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return event

# Update event
@app.put("/events/{event_id}", response_model=schemas.EventResponse)
def update_event(event_id: int, updated_event: schemas.EventCreate, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    difference = updated_event.total_seats - event.total_seats

    event.title = updated_event.title
    event.location = updated_event.location
    event.total_seats = updated_event.total_seats
    event.description = updated_event.description
    event.date_time = updated_event.date_time
    event.price = updated_event.price
    event.category = updated_event.category
    event.available_seats += difference

    db.commit()
    db.refresh(event)

    return event

# Delete event
@app.delete("/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    # 1. Check if event exists
    event = db.query(models.Event).filter(models.Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # 2. Check if any bookings exist for this event
    booking_exists = db.query(models.Booking).filter(
        models.Booking.event_id == event_id
    ).first()

    if booking_exists:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete event with existing bookings"
        )

    # 3. Delete event
    db.delete(event)
    db.commit()

    return {"message": "Event deleted"}

# Book event
@app.post("/book", response_model=schemas.BookingResponse)
def book_event(
    booking: schemas.BookingCreate,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    event = db.query(models.Event).filter(models.Event.id == booking.event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.available_seats < booking.tickets:
        raise HTTPException(status_code=400, detail="Not enough seats available")

    event.available_seats -= booking.tickets

    new_booking = models.Booking(
        user_name=username,
        event_id=booking.event_id,
        tickets=booking.tickets
    )

    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    return new_booking

# Get user bookings
@app.get("/my-bookings", response_model=list[schemas.BookingResponse])
def get_my_bookings(
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    return db.query(models.Booking).filter(models.Booking.user_name == username).all()

# Cancel booking
@app.delete("/book/{booking_id}")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.user_name != username:
        raise HTTPException(status_code=403, detail="Not allowed")

    event = db.query(models.Event).filter(models.Event.id == booking.event_id).first()

    if event:
        event.available_seats += booking.tickets

    db.delete(booking)
    db.commit()

    return {"message": "Booking cancelled"}

@app.get("/admin/bookings", response_model=list[schemas.BookingResponse])
def get_all_bookings(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    return db.query(models.Booking).all()


@app.get("/admin/bookings/filter", response_model=list[schemas.BookingResponse])
def filter_bookings(
    user_name: str | None = None,
    event_id: int | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    query = db.query(models.Booking)

    if user_name:
        query = query.filter(models.Booking.user_name == user_name)

    if event_id:
        query = query.filter(models.Booking.event_id == event_id)

    return query.all()

@app.delete("/admin/bookings/{booking_id}")
def admin_cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    event = db.query(models.Event).filter(models.Event.id == booking.event_id).first()

    if event:
        event.available_seats += booking.tickets

    db.delete(booking)
    db.commit()

    return {"message": "Booking cancelled by admin"}

@app.get("/admin/users", response_model=list[schemas.UserResponse])
def get_users(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    return db.query(models.User).all()

@app.get("/admin/users", response_model=list[schemas.UserResponse])
def get_users(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    return db.query(models.User).all()

@app.put("/admin/users/{user_id}/role")
def update_user_role(
    user_id: int,
    role: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    target_user = db.query(models.User).filter(models.User.id == user_id).first()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    target_user.role = role
    db.commit()

    return {"message": f"User role updated to {role}"}

@app.put("/admin/users/{user_id}/status")
def update_user_status(
    user_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    target_user = db.query(models.User).filter(models.User.id == user_id).first()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.is_active = is_active
    db.commit()

    return {"message": "User status updated"}