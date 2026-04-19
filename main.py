"""from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import Query
import os

# TOKEN BLACKLIST
blacklisted_tokens = set()

# PASSWORD RESET STORAGE
password_reset_tokens = {}

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

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# AUDIT LOG HELPER
def log_action(db, user, action):
    log = models.AuditLog(
        action=action,
        performed_by=user["username"]
    )
    db.add(log)
    db.commit()

# Get current user from token
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials

    # check blacklist
    blacklisted = db.query(models.BlacklistedToken).filter(models.BlacklistedToken.token == token).first()
    if blacklisted:
        raise HTTPException(status_code=401, detail="Token expired or logged out")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")

        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {"username": username, "role": role}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

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

    role = getattr(user, "role", "user")

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

    if not db_user.is_active:
        raise HTTPException(status_code=403, detail="User is blocked")

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
        description=event.description,
        date_time=event.date_time,
        price=event.price,
        category=event.category
    )

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    return db_event

@app.get("/events", response_model=list[schemas.EventResponse])
def get_events(
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    # Ensure valid values
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be >= 1")

    if limit < 1:
        raise HTTPException(status_code=400, detail="Limit must be >= 1")

    # Calculate offset
    skip = (page - 1) * limit

    # Fetch paginated results
    events = db.query(models.Event).offset(skip).limit(limit).all()

    return events

# Get events searched
from fastapi import Query

@app.get("/events/search", response_model=list[schemas.EventResponse])
def search_events(
    title: str | None = None,
    category: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    date: str | None = None,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db)
):

    # Search events with filters + pagination

    query = db.query(models.Event)

    # FILTER: title (partial match)
    if title:
        query = query.filter(models.Event.title.contains(title))

    # FILTER: category
    if category:
        query = query.filter(models.Event.category == category)

    # FILTER: price range
    if min_price is not None:
        query = query.filter(models.Event.price >= min_price)

    if max_price is not None:
        query = query.filter(models.Event.price <= max_price)

    # FILTER: date (simple string match for now)
    if date:
        query = query.filter(models.Event.date_time.contains(date))

    # PAGINATION
    skip = (page - 1) * limit
    events = query.offset(skip).limit(limit).all()

    return events

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
    event = db.query(models.Event).filter(models.Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    booking_exists = db.query(models.Booking).filter(
        models.Booking.event_id == event_id
    ).first()

    if booking_exists:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete event with existing bookings"
        )

    db.delete(event)
    db.commit()

    return {"message": "Event deleted"}

# Book event
@app.post("/book", response_model=schemas.BookingResponse)
def book_event(
    booking: schemas.BookingCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    event = db.query(models.Event).filter(models.Event.id == booking.event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.available_seats < booking.tickets:
        raise HTTPException(status_code=400, detail="Not enough seats available")

    event.available_seats -= booking.tickets

    new_booking = models.Booking(
        user_name=user["username"],
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
    user: dict = Depends(get_current_user)
):
    return db.query(models.Booking).filter(
        models.Booking.user_name == user["username"]
    ).all()

# Cancel booking
@app.delete("/book/{booking_id}")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.user_name != user["username"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    event = db.query(models.Event).filter(models.Event.id == booking.event_id).first()

    if event:
        event.available_seats += booking.tickets

    db.delete(booking)
    db.commit()

    return {"message": "Booking cancelled"}

# ADMIN: Get all bookings
@app.get("/admin/bookings", response_model=list[schemas.BookingResponse])
def get_all_bookings(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    return db.query(models.Booking).all()

# ADMIN: Filter bookings
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

# ADMIN: Cancel any booking
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

# ADMIN: Get all users
@app.get("/admin/users", response_model=list[schemas.UserResponse])
def get_users(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    return db.query(models.User).all()

# ADMIN: Update user role
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

# ADMIN: Block / Unblock user
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

@app.get("/admin/dashboard")
def admin_dashboard(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    # ONLY ADMIN ACCESS
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    # TOTAL USERS
    total_users = db.query(models.User).count()

    # TOTAL EVENTS
    total_events = db.query(models.Event).count()

    # TOTAL BOOKINGS
    total_bookings = db.query(models.Booking).count()

    # TOTAL TICKETS SOLD
    total_tickets = db.query(models.Booking).all()
    tickets_sum = sum(b.tickets for b in total_tickets)

    return {
        "total_users": total_users,
        "total_events": total_events,
        "total_bookings": total_bookings,
        "total_tickets_sold": tickets_sum
    }

@app.get("/admin/analytics/most-booked")
def most_booked_events(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    events = db.query(models.Event).all()

    result = []

    for event in events:
        total_bookings = db.query(models.Booking)\
            .filter(models.Booking.event_id == event.id)\
            .count()

        result.append({
            "event_id": event.id,
            "title": event.title,
            "bookings": total_bookings
        })

    # sort by most bookings
    result.sort(key=lambda x: x["bookings"], reverse=True)

    return result

@app.get("/admin/analytics/least-booked")
def least_booked_events(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    events = db.query(models.Event).all()

    result = []

    for event in events:
        total_bookings = db.query(models.Booking)\
            .filter(models.Booking.event_id == event.id)\
            .count()

        result.append({
            "event_id": event.id,
            "title": event.title,
            "bookings": total_bookings
        })

    result.sort(key=lambda x: x["bookings"])

    return result

@app.get("/admin/analytics/revenue")
def get_revenue(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    # Admin check
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    bookings = db.query(models.Booking).all()

    total_revenue = 0

    for booking in bookings:
        event = db.query(models.Event).filter(models.Event.id == booking.event_id).first()

        if event:
            total_revenue += booking.tickets * event.price

    return {
        "total_revenue": total_revenue
    }

@app.get("/admin/bookings/advanced")
def advanced_booking_filter(
    user_name: str | None = None,
    event_id: int | None = None,
    min_tickets: int | None = None,
    max_tickets: int | None = None,
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

    if min_tickets:
        query = query.filter(models.Booking.tickets >= min_tickets)

    if max_tickets:
        query = query.filter(models.Booking.tickets <= max_tickets)

    return query.all()

@app.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).all()

@app.post("/admin/categories")
def create_category(
    name: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    existing = db.query(models.Category).filter(models.Category.name == name).first()

    if existing:
        raise HTTPException(status_code=400, detail="Category exists")

    category = models.Category(name=name)
    db.add(category)
    db.commit()

    return {"message": "Category created"}

@app.post("/admin/notify")
def send_notification(
    message: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    notif = models.Notification(message=message)
    db.add(notif)
    db.commit()

    return {"message": "Notification sent"}


@app.post("/password-reset/request")
def request_reset(username: str, db: Session = Depends(get_db)):

    user = db.query(models.User).filter(models.User.username == username).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    def create_token(data: dict, expires_delta: timedelta | None = None):
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    reset_entry = models.PasswordReset(
        username=username,
        token=create_token(),
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )

    db.add(reset_entry)
    db.commit()

    return {"reset_token": create_token()}


@app.post("/password-reset/confirm")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):

    record = db.query(models.PasswordReset).filter(models.PasswordReset.token == token).first()

    if not record:
        raise HTTPException(status_code=400, detail="Invalid token")

    if record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expired")

    user = db.query(models.User).filter(models.User.username == record.username).first()

    user.password = hash_password(new_password)

    db.delete(record)
    db.commit()

    return {"message": "Password updated"}

@app.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    blacklisted = models.BlacklistedToken(token=token)
    db.add(blacklisted)
    db.commit()

    return {"message": "Logged out successfully"}


@app.post("/verify/request")
def send_verification(username: str, db: Session = Depends(get_db)):

    token = create_token({"sub": username})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.add(models.EmailVerification(username=username, token=token))
    db.commit()

    return {"verification_token": token}


@app.post("/verify/confirm")
def verify_account(token: str, db: Session = Depends(get_db)):

    data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = data.get("sub")

    user = db.query(models.User).filter(models.User.username == username).first()

    user.is_verified = True
    db.commit()

    return {"message": "Account verified"}"""


from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from database import engine
import models

from routers import auth, events, bookings, admin, analytics, engagement, profile, payment

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(events.router)
app.include_router(bookings.router)
app.include_router(admin.router)
app.include_router(analytics.router)
app.include_router(engagement.router)
app.include_router(profile.router)
app.include_router(payment.router)
