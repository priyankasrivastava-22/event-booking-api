from pydantic import BaseModel

class EventCreate(BaseModel):
    title: str
    location: str
    total_seats: int
    description: str | None = None
    date_time: str | None = None
    price: int = 0
    category: str | None = None

class EventResponse(BaseModel):
    id: int
    title: str
    location: str
    total_seats: int
    available_seats: int
    escription: str | None = None
    date_time: str | None = None
    price: int
    category: str | None = None

    class Config:
        from_attributes = True  # for SQLAlchemy -> Pydantic (v2)

class BookingCreate(BaseModel):
    user_name: str
    event_id: int
    tickets: int

class BookingResponse(BaseModel):
    id: int
    user_name: str
    event_id: int
    tickets: int
    booking_time: str | None = None

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True