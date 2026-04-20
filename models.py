from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from database import Base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

# ---------------- EVENT ----------------
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    location = Column(String)

    description = Column(String, nullable=True)
    date_time = Column(String, nullable=True)
    price = Column(Integer, default=0)
    category = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    total_seats = Column(Integer)
    available_seats = Column(Integer)

    category_rel = relationship("Category", back_populates="events")

# ---------------- BOOKING ----------------
class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String)
    event_id = Column(Integer, ForeignKey("events.id"))
    tickets = Column(Integer)

    booking_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    payment_status = Column(String, default="pending")

    event = relationship("Event")


# ---------------- USER ----------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    password = Column(String)

    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)

    profile_image = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    bio = Column(String, nullable=True)

    email = Column(String, unique=True, nullable=True)

    is_verified = Column(Boolean, default=False)

# ---------------- CATEGORY ----------------
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    events = relationship("Event", back_populates="category_rel")

# ---------------- NOTIFICATION ----------------
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(String)
    user_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ---------------- AUDIT LOG ----------------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String)
    performed_by = Column(String)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ---------------- BLACKLIST TOKEN ----------------
class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True)


# ---------------- PASSWORD RESET ----------------
class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    token = Column(String, unique=True)
    expires_at = Column(DateTime)


# ---------------- EMAIL VERIFICATION ----------------
class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    token = Column(String, unique=True)
    expires_at = Column(DateTime)

#----------------PAYMENT------------------------------
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    user_name = Column(String)

    amount = Column(Integer)
    status = Column(String, default="pending")  # pending / success / failed
    method = Column(String, default="mock")

    transaction_id = Column(String, unique=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


