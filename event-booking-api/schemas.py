from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class EventCreate(BaseModel):
    title: str
    location: str
    total_seats: int
    description: str | None = None
    date_time: str | None = None
    price: int = 0
    category_id: Optional[int] = None
    category: str | None = None


class EventResponse(BaseModel):
    id: int
    title: str
    location: str
    total_seats: int
    available_seats: int
    description: str | None = None
    date_time: str | None = None
    price: int
    category: str | None = None

    class Config:
        from_attributes = True


class BookingCreate(BaseModel):
    event_id: int
    tickets: int


class BookingResponse(BaseModel):
    id: int
    user_name: str
    event_id: int
    tickets: int
    booking_time: datetime | None = None  # FIXED type

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


class CategoryBase(BaseModel):
    name: str


class CategoryResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class CategoryCreate(BaseModel):
    name: str


class NotificationCreate(BaseModel):
    message: str
    user_name: Optional[str] = None


class NotificationBase(BaseModel):
    message: str


class NotificationResponse(BaseModel):
    id: int
    message: str

    class Config:
        from_attributes = True

class UserProfile(BaseModel):
    full_name: str | None = None
    bio: str | None = None
    email: str | None = None
    profile_image: str | None = None


class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    bio: str | None = None
    email: str | None = None


class PaymentCreate(BaseModel):
    booking_id: int
    method: str = "mock"

class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    user_name: str
    amount: int
    status: str
    transaction_id: str

    class Config:
        from_attributes = True

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None

class EventUpdate(BaseModel):
    title: Optional[str] = None
    location: Optional[str] = None
    total_seats: Optional[int] = None
    available_seats: Optional[int] = None
    description: Optional[str] = None
    date_time: Optional[str] = None
    price: Optional[int] = None
    category_id: Optional[int] = None

