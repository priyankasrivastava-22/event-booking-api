from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from database import Base
from sqlalchemy.orm import relationship
from datetime import datetime

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    location = Column(String)

    description = Column(String, nullable=True)
    date_time = Column(String, nullable=True)  # kept as string (no logic change)
    price = Column(Integer, default=0)
    category = Column(String, nullable=True)

    total_seats = Column(Integer)
    available_seats = Column(Integer)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String)
    event_id = Column(Integer, ForeignKey("events.id"))
    tickets = Column(Integer)

    booking_time = Column(DateTime, default=datetime.utcnow)

    payment_status = Column(String, default="pending")

    event = relationship("Event")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    password = Column(String)

    role = Column(String, default="user")   # user / admin
    is_active = Column(Boolean, default=True)  # block/unblock

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    action = Column(String)
    performed_by = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)