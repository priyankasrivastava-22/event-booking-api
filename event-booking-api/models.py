from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, UniqueConstraint, CheckConstraint, Index  # SQLAlchemy database definitions
from database import Base  # Shared declarative base
from sqlalchemy.orm import relationship  # ORM relationships
from datetime import datetime, timezone  # UTC timestamps


INVENTORY_SEAT = "seat"  # Fixed-seat inventory
INVENTORY_ZONE = "zone"  # Zone-based inventory
INVENTORY_GENERAL = "general"  # General admission inventory

INVENTORY_AVAILABLE = "available"  # Inventory available for sale
INVENTORY_LOCKED = "locked"  # Inventory temporarily held
INVENTORY_SOLD = "sold"  # Inventory sold
INVENTORY_INACTIVE = "inactive"  # Inventory disabled

SEAT_AVAILABLE = "available"  # Seat available
SEAT_LOCKED = "locked"  # Seat temporarily locked
SEAT_SOLD = "sold"  # Seat sold

LOCK_ACTIVE = "active"  # Lock currently active
LOCK_EXPIRED = "expired"  # Lock expired
LOCK_RELEASED = "released"  # Lock released
LOCK_CONVERTED = "converted"  # Lock converted into booking

BOOKING_PENDING = "pending"  # Booking created but not completed
BOOKING_HELD = "held"  # Inventory successfully held
BOOKING_CONFIRMED = "confirmed"  # Booking successfully paid
BOOKING_CANCELLED = "cancelled"  # Booking cancelled
BOOKING_EXPIRED = "expired"  # Booking hold expired
BOOKING_FAILED = "failed"  # Booking/payment failed

PAYMENT_PENDING = "pending"  # Payment initiated
PAYMENT_SUCCESS = "success"  # Payment completed
PAYMENT_FAILED = "failed"  # Payment failed
PAYMENT_REFUNDED = "refunded"  # Payment refunded

TICKET_CONFIRMED = "confirmed"  # Ticket issued
TICKET_CANCELLED = "cancelled"  # Ticket cancelled
TICKET_USED = "used"  # Ticket consumed at entry


class Event(Base):  # EVENT
    __tablename__ = "events"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Unique event ID
    title = Column(String, nullable=False)  # Event title
    location = Column(String, nullable=False)  # Event location
    description = Column(String, nullable=True)  # Event description
    date_time = Column(String, nullable=True)  # Event date and time
    price = Column(Integer, default=0, nullable=False)  # Legacy/base event price
    image_url = Column(String, nullable=True)  # Cloudinary event image
    category = Column(String, nullable=True)  # Legacy category name
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)  # Category reference
    total_seats = Column(Integer, default=0, nullable=False)  # Legacy total inventory
    available_seats = Column(Integer, default=0, nullable=False)  # Legacy available inventory
    inventory_type = Column(String, default=INVENTORY_GENERAL, nullable=False, index=True)  # Event inventory model

    category_rel = relationship("Category", back_populates="events")  # Category relationship
    layouts = relationship("VenueLayout", back_populates="event", cascade="all, delete-orphan")  # Venue layouts
    zones = relationship("EventZone", back_populates="event", cascade="all, delete-orphan")  # Event zones
    rows = relationship("VenueRow", back_populates="event", cascade="all, delete-orphan")  # Venue rows
    seats = relationship("Seat", back_populates="event", cascade="all, delete-orphan")  # Event seats
    ticket_types = relationship("TicketType", back_populates="event", cascade="all, delete-orphan")  # Ticket types
    inventories = relationship("Inventory", back_populates="event", cascade="all, delete-orphan")  # Sellable inventory
    bookings = relationship("Booking", back_populates="event")  # Event bookings
    tickets_rel = relationship("Ticket", back_populates="event")  # Event tickets


class VenueLayout(Base):  # VENUE LAYOUT
    __tablename__ = "venue_layouts"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Layout ID
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)  # Event reference
    name = Column(String, nullable=False)  # Layout name
    version = Column(Integer, default=1, nullable=False)  # Layout version
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # Active layout
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)  # Creation timestamp

    event = relationship("Event", back_populates="layouts")  # Event relationship
    zones = relationship("EventZone", back_populates="layout", cascade="all, delete-orphan")  # Layout zones

    __table_args__ = (  # Layout constraints
        UniqueConstraint("event_id", "version", name="uq_event_layout_version"),  # One version per event
        Index("ix_layout_event_active", "event_id", "is_active"),  # Active layout lookup
    )


class EventZone(Base):  # EVENT ZONE
    __tablename__ = "event_zones"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Zone ID
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)  # Event reference
    layout_id = Column(Integer, ForeignKey("venue_layouts.id", ondelete="CASCADE"), nullable=True, index=True)  # Layout reference
    name = Column(String, nullable=False)  # Zone name
    code = Column(String, nullable=False)  # Zone code
    zone_type = Column(String, nullable=False, default="seated", index=True)  # Seated or general admission
    capacity = Column(Integer, default=0, nullable=False)  # Zone capacity
    sold_count = Column(Integer, default=0, nullable=False)  # Sold inventory count
    locked_count = Column(Integer, default=0, nullable=False)  # Held inventory count
    base_price = Column(Integer, default=0, nullable=False)  # Base zone price
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # Zone active state

    event = relationship("Event", back_populates="zones")  # Event relationship
    layout = relationship("VenueLayout", back_populates="zones")  # Layout relationship
    rows = relationship("VenueRow", back_populates="zone", cascade="all, delete-orphan")  # Zone rows
    seats = relationship("Seat", back_populates="zone", cascade="all, delete-orphan")  # Zone seats
    inventories = relationship("Inventory", back_populates="zone")  # Zone inventory
    tickets = relationship("Ticket", back_populates="zone")  # Zone tickets
    ticket_types = relationship("TicketType", back_populates="zone")  # Zone ticket types

    __table_args__ = (  # Zone constraints
        UniqueConstraint("event_id", "code", name="uq_event_zone_code"),  # Unique zone code per event
        CheckConstraint("capacity >= 0", name="ck_zone_capacity_non_negative"),  # Valid capacity
        CheckConstraint("sold_count >= 0", name="ck_zone_sold_non_negative"),  # Valid sold count
        CheckConstraint("locked_count >= 0", name="ck_zone_locked_non_negative"),  # Valid locked count
        CheckConstraint("base_price >= 0", name="ck_base_price_non_negative"),  # Valid price
    )


class VenueRow(Base):  # VENUE ROW
    __tablename__ = "venue_rows"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Row ID
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)  # Event reference
    zone_id = Column(Integer, ForeignKey("event_zones.id", ondelete="CASCADE"), nullable=False, index=True)  # Zone reference
    row_label = Column(String, nullable=False)  # Display row label
    row_number = Column(Integer, nullable=False)  # Numeric row position

    event = relationship("Event", back_populates="rows")  # Event relationship
    zone = relationship("EventZone", back_populates="rows")  # Zone relationship
    seats = relationship("Seat", back_populates="row", cascade="all, delete-orphan")  # Row seats

    __table_args__ = (  # Row constraints
        UniqueConstraint("zone_id", "row_label", name="uq_zone_row_label"),  # Unique row label
        UniqueConstraint("zone_id", "row_number", name="uq_zone_row_number"),  # Unique row number
        CheckConstraint("row_number > 0", name="ck_row_number_positive"),  # Valid row number
    )


class Seat(Base):  # SEAT
    __tablename__ = "seats"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Seat ID
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)  # Event reference
    zone_id = Column(Integer, ForeignKey("event_zones.id", ondelete="CASCADE"), nullable=False, index=True)  # Zone reference
    row_id = Column(Integer, ForeignKey("venue_rows.id", ondelete="CASCADE"), nullable=False, index=True)  # Row reference
    seat_number = Column(Integer, nullable=False)  # Seat number
    seat_code = Column(String, nullable=False, index=True)  # Public seat code
    status = Column(String, default=SEAT_AVAILABLE, nullable=False, index=True)  # Seat state
    price = Column(Integer, nullable=False)  # Seat price
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # Seat active state

    event = relationship("Event", back_populates="seats")  # Event relationship
    zone = relationship("EventZone", back_populates="seats")  # Zone relationship
    row = relationship("VenueRow", back_populates="seats")  # Row relationship
    inventory = relationship("Inventory", back_populates="seat", uselist=False, cascade="all, delete-orphan")  # Sellable seat inventory
    locks = relationship("SeatLock", back_populates="seat", cascade="all, delete-orphan")  # Seat locks
    tickets = relationship("Ticket", back_populates="seat")  # Seat tickets

    __table_args__ = (  # Seat constraints
        UniqueConstraint("event_id", "seat_code", name="uq_event_seat_code"),  # Unique seat code
        UniqueConstraint("row_id", "seat_number", name="uq_row_seat_number"),  # Unique seat within row
        CheckConstraint("seat_number > 0", name="ck_seat_number_positive"),  # Valid seat number
        CheckConstraint("price >= 0", name="ck_seat_price_non_negative"),  # Valid seat price
    )


class TicketType(Base):  # TICKET TYPE / PASS
    __tablename__ = "ticket_types"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Ticket type ID
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)  # Event reference
    zone_id = Column(Integer, ForeignKey("event_zones.id", ondelete="SET NULL"), nullable=True, index=True)  # Optional zone reference
    name = Column(String, nullable=False)  # Ticket/pass name
    price = Column(Integer, nullable=False)  # Ticket/pass price
    inventory_limit = Column(Integer, nullable=True)  # Maximum inventory
    sold_count = Column(Integer, default=0, nullable=False)  # Sold count
    locked_count = Column(Integer, default=0, nullable=False)  # Currently held (not yet paid) count  -  mirrors EventZone.locked_count so pass holds can't oversell under concurrency
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # Active state

    event = relationship("Event", back_populates="ticket_types")  # Event relationship
    zone = relationship("EventZone", back_populates="ticket_types")  # Zone relationship
    inventory = relationship("Inventory", back_populates="ticket_type", uselist=False)  # General/pass inventory
    tickets = relationship("Ticket", back_populates="ticket_type")  # Tickets

    __table_args__ = (  # Ticket type constraints
        UniqueConstraint("event_id", "name", name="uq_event_ticket_type"),  # Unique ticket type
        CheckConstraint("price >= 0", name="ck_ticket_price_non_negative"),  # Valid price
        CheckConstraint("inventory_limit IS NULL OR inventory_limit >= 0", name="ck_ticket_inventory_non_negative"),  # Valid inventory limit
        CheckConstraint("sold_count >= 0", name="ck_ticket_sold_non_negative"),  # Valid sold count
        CheckConstraint("locked_count >= 0", name="ck_ticket_locked_non_negative"),  # Valid locked count
    )


class Inventory(Base):  # GENERIC SELLABLE INVENTORY
    __tablename__ = "inventories"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Inventory ID
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)  # Event reference
    inventory_type = Column(String, nullable=False, index=True)  # Seat, zone or general
    status = Column(String, default=INVENTORY_AVAILABLE, nullable=False, index=True)  # Inventory state
    price = Column(Integer, nullable=False, default=0)  # Current sell price
    seat_id = Column(Integer, ForeignKey("seats.id", ondelete="CASCADE"), nullable=True, unique=True, index=True)  # Optional physical seat
    zone_id = Column(Integer, ForeignKey("event_zones.id", ondelete="CASCADE"), nullable=True, index=True)  # Optional zone inventory
    ticket_type_id = Column(Integer, ForeignKey("ticket_types.id", ondelete="CASCADE"), nullable=True, unique=True, index=True)  # Optional pass inventory
    lock_token = Column(String, nullable=True, unique=True, index=True)  # Active inventory lock token
    locked_until = Column(DateTime(timezone=True), nullable=True, index=True)  # Inventory lock expiration
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)  # Creation timestamp
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)  # Update timestamp

    event = relationship("Event", back_populates="inventories")  # Event relationship
    seat = relationship("Seat", back_populates="inventory")  # Physical seat relationship
    zone = relationship("EventZone", back_populates="inventories")  # Zone relationship
    ticket_type = relationship("TicketType", back_populates="inventory")  # Ticket/pass relationship
    booking_items = relationship("BookingItem", back_populates="inventory")  # Booking items

    __table_args__ = (  # Inventory constraints
        Index("ix_inventory_event_status", "event_id", "status"),  # Fast availability lookup
        Index("ix_inventory_event_type", "event_id", "inventory_type"),  # Fast inventory type lookup
    )


class SeatLock(Base):  # FIXED SEAT LOCK
    __tablename__ = "seat_locks"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Lock ID
    seat_id = Column(Integer, ForeignKey("seats.id", ondelete="CASCADE"), nullable=False, index=True)  # Seat reference
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)  # User reference
    lock_token = Column(String, unique=True, nullable=False, index=True)  # Secure lock token
    locked_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)  # Lock creation
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)  # Lock expiration
    released_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Release timestamp
    status = Column(String, default=LOCK_ACTIVE, nullable=False, index=True)  # Lock lifecycle state

    seat = relationship("Seat", back_populates="locks")  # Seat relationship
    user = relationship("User", back_populates="seat_locks")  # User relationship

    __table_args__ = (  # Lock indexes
        Index("ix_active_seat_lock", "seat_id", "status"),  # Active seat lock lookup
        Index("ix_user_active_lock", "user_id", "status"),  # User active lock lookup
        Index("ix_lock_expiration", "status", "expires_at"),  # Expired lock cleanup
    )


class Booking(Base):  # BOOKING / HOLD / ORDER
    __tablename__ = "bookings"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Booking ID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)  # Immutable user ID
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)  # Event ID
    tickets = Column(Integer, nullable=False)  # Legacy ticket quantity
    status = Column(String, default=BOOKING_PENDING, nullable=False, index=True)  # Booking lifecycle state
    total_amount = Column(Integer, default=0, nullable=False)  # Booking total amount
    idempotency_key = Column(String, nullable=True, unique=True, index=True)  # Prevent duplicate booking requests
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Hold expiration
    booking_time = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)  # Booking timestamp
    payment_status = Column(String, default=PAYMENT_PENDING, nullable=False, index=True)  # Legacy payment lifecycle

    user = relationship("User", back_populates="bookings")  # User relationship
    event = relationship("Event", back_populates="bookings")  # Event relationship
    items = relationship("BookingItem", back_populates="booking", cascade="all, delete-orphan")  # Inventory items
    tickets_rel = relationship("Ticket", back_populates="booking", cascade="all, delete-orphan")  # Issued tickets
    payment = relationship("Payment", back_populates="booking", uselist=False, cascade="all, delete-orphan")  # Booking payment

    __table_args__ = (  # Booking indexes
        Index("ix_booking_user_event", "user_id", "event_id"),  # User event lookup
        Index("ix_booking_event_status", "event_id", "status"),  # Event booking status lookup
        Index("ix_booking_expiration", "status", "expires_at"),  # Hold expiration lookup
    )


class BookingItem(Base):  # BOOKING ITEM
    __tablename__ = "booking_items"  # Booking inventory item

    id = Column(Integer, primary_key=True, index=True)  # Booking item ID
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)  # Booking reference
    inventory_id = Column(Integer, ForeignKey("inventories.id", ondelete="RESTRICT"), nullable=False, index=True)  # Inventory reference
    quantity = Column(Integer, default=1, nullable=False)  # Number of inventory units held
    price = Column(Integer, nullable=False)  # Price captured at booking time
    status = Column(String, default=BOOKING_HELD, nullable=False, index=True)  # Item lifecycle state
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)  # Creation time

    booking = relationship("Booking", back_populates="items")  # Booking relationship
    inventory = relationship("Inventory", back_populates="booking_items")  # Inventory relationship

    __table_args__ = (  # Booking item constraints
        UniqueConstraint("booking_id", "inventory_id", name="uq_booking_inventory"),  # Prevent duplicate inventory in booking
        CheckConstraint("quantity > 0", name="ck_booking_item_quantity_positive"),  # Quantity must be positive
        CheckConstraint("price >= 0", name="ck_booking_item_price_non_negative"),  # Price cannot be negative
    )


class Ticket(Base):  # ISSUED TICKET
    __tablename__ = "tickets"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Ticket ID
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)  # Booking reference
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)  # Event reference
    seat_id = Column(Integer, ForeignKey("seats.id", ondelete="SET NULL"), nullable=True, index=True)  # Optional seat
    zone_id = Column(Integer, ForeignKey("event_zones.id", ondelete="SET NULL"), nullable=True, index=True)  # Optional zone
    ticket_type_id = Column(Integer, ForeignKey("ticket_types.id", ondelete="SET NULL"), nullable=True, index=True)  # Optional ticket type
    ticket_code = Column(String, unique=True, nullable=False, index=True)  # Unique public ticket code
    qr_token = Column(String, unique=True, nullable=False, index=True)  # QR verification token
    price_paid = Column(Integer, nullable=False)  # Actual paid price
    status = Column(String, default=TICKET_CONFIRMED, nullable=False, index=True)  # Ticket state
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)  # Ticket creation
    used_at = Column(DateTime(timezone=True), nullable=True)  # Ticket usage timestamp

    booking = relationship("Booking", back_populates="tickets_rel")  # Booking relationship
    event = relationship("Event", back_populates="tickets_rel")  # Event relationship
    seat = relationship("Seat", back_populates="tickets")  # Seat relationship
    zone = relationship("EventZone", back_populates="tickets")  # Zone relationship
    ticket_type = relationship("TicketType", back_populates="tickets")  # Ticket type relationship


class User(Base):  # USER
    __tablename__ = "users"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Immutable internal user ID
    username = Column(String, unique=True, nullable=False, index=True)  # Login username
    password = Column(String, nullable=False)  # Password hash
    role = Column(String, default="user", nullable=False, index=True)  # User role
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # Account state
    profile_image = Column(String, nullable=True)  # Cloudinary profile image
    full_name = Column(String, nullable=True)  # Full name
    bio = Column(String, nullable=True)  # Biography
    email = Column(String, unique=True, nullable=True, index=True)  # Email address
    is_verified = Column(Boolean, default=False, nullable=False)  # Legacy account verification
    phone_encrypted = Column(String, nullable=True)  # Encrypted phone
    phone_lookup_hmac = Column(String, unique=True, index=True, nullable=True)  # Deterministic phone lookup
    email_verified = Column(Boolean, default=False, nullable=False)  # Email verification state
    phone_verified = Column(Boolean, default=False, nullable=False)  # Phone verification state
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)  # Account creation
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)  # Account update

    bookings = relationship("Booking", back_populates="user")  # User bookings
    payments = relationship("Payment", back_populates="user")  # User payments
    notifications = relationship("Notification", back_populates="user")  # User notifications
    audit_logs = relationship("AuditLog", back_populates="user")  # User audit logs
    seat_locks = relationship("SeatLock", back_populates="user")  # User seat locks
    password_resets = relationship("PasswordReset", back_populates="user", cascade="all, delete-orphan")  # Password resets
    email_verifications = relationship("EmailVerification", back_populates="user", cascade="all, delete-orphan")  # Email verification
    otp_verifications = relationship("OTPVerification", back_populates="user", cascade="all, delete-orphan")  # OTP verification


class Category(Base):  # CATEGORY
    __tablename__ = "categories"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Category ID
    name = Column(String, unique=True, nullable=False)  # Category name

    events = relationship("Event", back_populates="category_rel")  # Category events


class Notification(Base):  # NOTIFICATION
    __tablename__ = "notifications"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Notification ID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)  # User reference
    message = Column(String, nullable=False)  # Notification message
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)  # Notification timestamp

    user = relationship("User", back_populates="notifications")  # User relationship


class BlacklistedToken(Base):  # JWT BLACKLIST
    __tablename__ = "blacklisted_tokens"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Blacklist ID
    token = Column(String, unique=True, nullable=False, index=True)  # Blacklisted JWT


class PasswordReset(Base):  # PASSWORD RESET
    __tablename__ = "password_resets"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Reset ID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)  # User reference
    token = Column(String, unique=True, nullable=False, index=True)  # Reset token
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)  # Token expiration

    user = relationship("User", back_populates="password_resets")  # User relationship


class EmailVerification(Base):  # EMAIL VERIFICATION
    __tablename__ = "email_verifications"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Verification ID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)  # User reference
    token = Column(String, unique=True, nullable=False, index=True)  # Verification token
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)  # Token expiration

    user = relationship("User", back_populates="email_verifications")  # User relationship


class OTPVerification(Base):  # OTP VERIFICATION
    __tablename__ = "otp_verifications"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # OTP ID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)  # User reference
    purpose = Column(String, nullable=False, index=True)  # OTP purpose
    destination = Column(String, nullable=False)  # OTP destination
    otp_hash = Column(String, nullable=False)  # Hashed OTP
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)  # OTP expiration
    attempts = Column(Integer, default=0, nullable=False)  # Verification attempts
    verified = Column(Boolean, default=False, nullable=False)  # Verification state
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)  # Creation timestamp
    used_at = Column(DateTime(timezone=True), nullable=True)  # OTP usage timestamp
    verification_token = Column(String, nullable=True, unique=True)  # Temporary verification token
    verification_token_expires_at = Column(DateTime(timezone=True), nullable=True)  # Verification token expiration

    user = relationship("User", back_populates="otp_verifications")  # User relationship


class Payment(Base):  # PAYMENT
    __tablename__ = "payments"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Payment ID
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)  # Booking reference
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)  # Immutable user reference
    amount = Column(Integer, nullable=False)  # Payment amount
    status = Column(String, default=PAYMENT_PENDING, nullable=False, index=True)  # Payment lifecycle
    method = Column(String, default="mock", nullable=False)  # Payment method
    transaction_id = Column(String, unique=True, nullable=False, index=True)  # Internal transaction ID
    provider = Column(String, nullable=True)  # External payment provider
    provider_payment_id = Column(String, nullable=True, unique=True, index=True)  # External provider payment ID
    currency = Column(String, default="INR", nullable=False)  # Payment currency
    failure_reason = Column(String, nullable=True)  # Payment failure reason
    webhook_event_id = Column(String, nullable=True, unique=True, index=True)  # Gateway webhook event ID
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)  # Payment creation
    paid_at = Column(DateTime(timezone=True), nullable=True)  # Successful payment timestamp
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)  # Payment update

    user = relationship("User", back_populates="payments")  # User relationship
    booking = relationship("Booking", back_populates="payment")  # Booking relationship


class AuditLog(Base):  # AUDIT LOG
    __tablename__ = "audit_logs"  # Database table

    id = Column(Integer, primary_key=True, index=True)  # Audit ID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)  # User reference
    action = Column(String, nullable=False)  # Action performed
    performed_by = Column(String, nullable=True)  # Actor information
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)  # Audit timestamp

    user = relationship("User", back_populates="audit_logs")  # User relationship