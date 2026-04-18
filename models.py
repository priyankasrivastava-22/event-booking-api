from sqlalchemy import Column, Integer, String, ForeignKey
from database import Base
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy import Column, Integer, String, Boolean

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    location = Column(String)

    description = Column(String, nullable=True)
    date_time = Column(String, nullable=True)  # keep string for now (simple)
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

    event = relationship("Event")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    password = Column(String)

    role = Column(String, default="user")  # user / admin
    is_active = Column(Boolean, default=True)  # for block/unblock