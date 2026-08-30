from pydantic import BaseModel, Field, ConfigDict  # Pydantic validation and ORM support
from datetime import datetime  # Timestamp type
from typing import Optional, List  # Optional values and lists


# ============================================================
# EVENT SCHEMAS
# ============================================================

class EventCreate(BaseModel):  # Event creation request
    title: str  # Event title
    location: str  # Event location
    total_seats: int = Field(default=0, ge=0)  # Legacy total inventory
    description: Optional[str] = None  # Event description
    date_time: Optional[str] = None  # Event date and time
    price: int = Field(default=0, ge=0)  # Base event price
    image_url: Optional[str] = None  # Cloudinary image URL
    category_id: Optional[int] = None  # Category ID
    category: Optional[str] = None  # Legacy category name
    inventory_type: str = "general"  # seat, zone or general inventory


class EventUpdate(BaseModel):  # Event update request
    title: Optional[str] = None  # Event title
    location: Optional[str] = None  # Event location
    total_seats: Optional[int] = Field(default=None, ge=0)  # Legacy total inventory
    available_seats: Optional[int] = Field(default=None, ge=0)  # Legacy available inventory
    description: Optional[str] = None  # Event description
    date_time: Optional[str] = None  # Event date and time
    price: Optional[int] = Field(default=None, ge=0)  # Base event price
    image_url: Optional[str] = None  # Cloudinary image URL
    category: Optional[str] = None  # Legacy category name
    category_id: Optional[int] = None  # Category ID
    inventory_type: Optional[str] = None  # Inventory model


class EventResponse(BaseModel):  # Event response
    id: int  # Event ID
    title: str  # Event title
    location: str  # Event location
    total_seats: int  # Legacy total inventory
    available_seats: int  # Legacy available inventory
    description: Optional[str] = None  # Event description
    date_time: Optional[str] = None  # Event date and time
    price: int  # Base event price
    image_url: Optional[str] = None  # Event image
    category: Optional[str] = None  # Category name
    category_id: Optional[int] = None  # Category ID
    inventory_type: str  # Inventory model

    model_config = ConfigDict(from_attributes=True)  # Enable SQLAlchemy ORM conversion


# ============================================================
# VENUE LAYOUT SCHEMAS
# ============================================================

class LayoutCreate(BaseModel):  # Create venue layout
    event_id: int  # Event ID
    name: str  # Layout name
    version: int = Field(default=1, ge=1)  # Layout version
    is_active: bool = True  # Active layout state


class VenueLayoutCreate(BaseModel):  # Create venue layout without explicit event ID
    name: str  # Layout name
    version: int = Field(default=1, ge=1)  # Layout version


class LayoutResponse(BaseModel):  # Venue layout response
    id: int  # Layout ID
    event_id: int  # Event ID
    name: str  # Layout name
    version: int  # Layout version
    is_active: bool  # Active state
    created_at: datetime  # Creation timestamp

    model_config = ConfigDict(from_attributes=True)  # Enable SQLAlchemy ORM conversion


class VenueLayoutResponse(LayoutResponse):  # Backward-compatible venue layout response
    pass  # Reuse layout response fields


# ============================================================
# EVENT ZONE SCHEMAS
# ============================================================

class EventZoneCreate(BaseModel):  # Create event zone
    event_id: int  # Event ID
    layout_id: Optional[int] = None  # Optional layout ID
    name: str  # Zone name
    code: str  # Unique zone code
    zone_type: str = "seated"  # Seated or general admission zone
    capacity: int = Field(default=0, ge=0)  # Zone capacity
    base_price: int = Field(default=0, ge=0)  # Zone base price


class ZoneCreate(EventZoneCreate):  # Backward-compatible zone creation schema
    is_active: bool = True  # Active zone state


class ZoneUpdate(BaseModel):  # Update event zone
    name: Optional[str] = None  # Zone name
    code: Optional[str] = None  # Zone code
    zone_type: Optional[str] = None  # Zone type
    capacity: Optional[int] = Field(default=None, ge=0)  # Zone capacity
    base_price: Optional[int] = Field(default=None, ge=0)  # Zone price
    is_active: Optional[bool] = None  # Active state


class EventZoneResponse(BaseModel):  # Event zone response
    id: int  # Zone ID
    event_id: int  # Event ID
    layout_id: Optional[int] = None  # Layout ID
    name: str  # Zone name
    code: str  # Zone code
    zone_type: str  # Zone type
    capacity: int  # Zone capacity
    sold_count: int  # Sold quantity
    locked_count: int  # Currently held quantity
    base_price: int  # Zone price
    is_active: bool  # Active state

    model_config = ConfigDict(from_attributes=True)  # Enable SQLAlchemy ORM conversion


class ZoneResponse(EventZoneResponse):  # Backward-compatible zone response
    pass  # Reuse event zone response fields


# ============================================================
# VENUE ROW SCHEMAS
# ============================================================

class VenueRowCreate(BaseModel):  # Create venue row
    event_id: int  # Event ID
    zone_id: int  # Zone ID
    row_label: str  # Display row label
    row_number: int = Field(gt=0)  # Numeric row position


class RowCreate(VenueRowCreate):  # Backward-compatible row creation schema
    pass  # Reuse venue row fields


class VenueRowResponse(BaseModel):  # Venue row response
    id: int  # Row ID
    event_id: int  # Event ID
    zone_id: int  # Zone ID
    row_label: str  # Row label
    row_number: int  # Row number

    model_config = ConfigDict(from_attributes=True)  # Enable SQLAlchemy ORM conversion


class RowResponse(VenueRowResponse):  # Backward-compatible row response
    pass  # Reuse venue row response fields


# ============================================================
# SEAT SCHEMAS
# ============================================================

class SeatCreate(BaseModel):  # Create physical seat
    event_id: int  # Event ID
    zone_id: int  # Zone ID
    row_id: int  # Row ID
    seat_number: int = Field(gt=0)  # Seat number
    seat_code: str  # Public seat code
    price: int = Field(ge=0)  # Seat price
    status: str = "available"  # Initial seat status
    is_active: bool = True  # Active seat state


class SeatUpdate(BaseModel):  # Update seat
    seat_number: Optional[int] = Field(default=None, gt=0)  # Seat number
    seat_code: Optional[str] = None  # Seat code
    price: Optional[int] = Field(default=None, ge=0)  # Seat price
    status: Optional[str] = None  # Seat status
    is_active: Optional[bool] = None  # Active state


class SeatResponse(BaseModel):  # Seat response
    id: int  # Seat ID
    event_id: int  # Event ID
    zone_id: int  # Zone ID
    row_id: int  # Row ID
    seat_number: int  # Seat number
    seat_code: str  # Seat code
    status: str  # Seat state
    price: int  # Seat price
    is_active: bool  # Active state

    model_config = ConfigDict(from_attributes=True)  # Enable SQLAlchemy ORM conversion


# ============================================================
# TICKET TYPE / PASS SCHEMAS
# ============================================================

class TicketTypeCreate(BaseModel):  # Create ticket type or pass
    event_id: int  # Event ID
    zone_id: Optional[int] = None  # Optional zone
    name: str  # Ticket/pass name
    price: int = Field(ge=0)  # Ticket/pass price
    inventory_limit: Optional[int] = Field(default=None, ge=0)  # Maximum inventory
    is_active: bool = True  # Active state


class TicketTypeUpdate(BaseModel):  # Update ticket type or pass
    name: Optional[str] = None  # Ticket/pass name
    zone_id: Optional[int] = None  # Optional zone
    price: Optional[int] = Field(default=None, ge=0)  # Ticket/pass price
    inventory_limit: Optional[int] = Field(default=None, ge=0)  # Maximum inventory
    is_active: Optional[bool] = None  # Active state


class TicketTypeResponse(BaseModel):  # Ticket type response
    id: int  # Ticket type ID
    event_id: int  # Event ID
    zone_id: Optional[int] = None  # Zone ID
    name: str  # Ticket/pass name
    price: int  # Ticket/pass price
    inventory_limit: Optional[int] = None  # Inventory limit
    sold_count: int  # Sold quantity
    is_active: bool  # Active state

    model_config = ConfigDict(from_attributes=True)  # Enable SQLAlchemy ORM conversion


# ============================================================
# INVENTORY SCHEMAS
# ============================================================

class InventoryResponse(BaseModel):  # Generic inventory response
    id: int  # Inventory ID
    event_id: int  # Event ID
    inventory_type: str  # seat, zone or general
    status: str  # available, locked, sold or inactive
    price: int  # Current inventory price
    seat_id: Optional[int] = None  # Physical seat reference
    zone_id: Optional[int] = None  # Zone inventory reference
    ticket_type_id: Optional[int] = None  # Pass inventory reference
    lock_token: Optional[str] = None  # Active lock token
    locked_until: Optional[datetime] = None  # Lock expiration
    created_at: datetime  # Inventory creation time
    updated_at: datetime  # Last inventory update time

    model_config = ConfigDict(from_attributes=True)  # Enable SQLAlchemy ORM conversion


class InventoryHoldRequest(BaseModel):  # Generic inventory hold request
    event_id: int  # Event ID
    inventory_ids: List[int] = Field(default_factory=list)  # Selected inventory IDs
    zone_id: Optional[int] = None  # Zone ID for zone inventory
    ticket_type_id: Optional[int] = None  # Ticket/pass ID
    quantity: int = Field(default=1, gt=0)  # Number of units requested
    idempotency_key: str  # Unique client request key


class InventoryHoldResponse(BaseModel):  # Inventory hold response
    booking_id: int  # Booking/hold ID
    event_id: int  # Event ID
    status: str  # Hold status
    total_amount: int  # Total held amount
    expires_at: datetime  # Hold expiration
    items: List["BookingItemResponse"]  # Held inventory items


class InventoryConfirmRequest(BaseModel):  # Inventory confirmation request
    booking_id: int  # Booking being confirmed


class InventoryValidationRequest(BaseModel):  # Validate inventory before hold
    event_id: int  # Event ID
    inventory_ids: List[int] = Field(min_length=1)  # Inventory IDs to validate


class InventoryValidationResponse(BaseModel):  # Inventory validation result
    event_id: int  # Event ID
    valid: bool  # Whether requested inventory is currently available
    inventory_ids: List[int]  # Requested inventory IDs
    unavailable_ids: List[int] = []  # Inventory IDs that cannot be held
    expired_released_ids: List[int] = []  # Expired locks released during validation


# ============================================================
# INVENTORY HOLD SCHEMAS
# ============================================================

class HoldCreate(BaseModel):  # Generic inventory hold request
    event_id: int  # Event ID
    inventory_ids: List[int] = Field(min_length=1)  # Inventory rows requested
    idempotency_key: str = Field(min_length=1, max_length=255)  # Duplicate request protection
    hold_seconds: int = Field(default=900, ge=60, le=1800)  # Default 15-minute hold


class HoldResponse(BaseModel):  # Generic inventory hold response
    booking_id: int  # Booking/hold ID
    event_id: int  # Event ID
    status: str  # Hold status
    total_amount: int  # Total held amount
    expires_at: datetime  # Hold expiration
    items: List["BookingItemResponse"]  # Held inventory items

    model_config = ConfigDict(from_attributes=True)  # Enable SQLAlchemy ORM conversion


class SeatHoldCreate(BaseModel):  # Fixed-seat hold request
    event_id: int  # Event ID
    seat_ids: List[int] = Field(min_length=1)  # Seats requested
    idempotency_key: Optional[str] = None  # Optional duplicate request protection
    hold_seconds: int = Field(default=900, ge=60, le=1800)  # Default 15-minute hold


class SeatHoldResponse(BaseModel):  # Fixed-seat hold response
    lock_token: str  # Unique seat lock token
    seat_ids: List[int]  # Held seat IDs
    expires_at: datetime  # Lock expiration
    status: str  # Lock status


class ZoneHoldCreate(BaseModel):  # Zone hold request
    event_id: int  # Event ID
    zone_id: int  # Zone ID
    quantity: int = Field(gt=0)  # Number of zone tickets requested
    idempotency_key: Optional[str] = None  # Optional duplicate request protection
    hold_seconds: int = Field(default=900, ge=60, le=1800)  # Default 15-minute hold


class PassHoldCreate(BaseModel):  # General/pass hold request
    event_id: int  # Event ID
    ticket_type_id: int  # Ticket/pass type ID
    quantity: int = Field(gt=0)  # Number of passes requested
    idempotency_key: Optional[str] = None  # Optional duplicate request protection
    hold_seconds: int = Field(default=900, ge=60, le=1800)  # Default 15-minute hold


# ============================================================
# INVENTORY RELEASE SCHEMAS
# ============================================================

class InventoryReleaseRequest(BaseModel):  # Release inventory request
    booking_id: Optional[int] = None  # Booking whose inventory should be released
    inventory_ids: Optional[List[int]] = None  # Specific inventory rows to release
    lock_token: Optional[str] = None  # Lock token for ownership verification


class InventoryReleaseResponse(BaseModel):  # Inventory release response
    released: bool  # Whether release succeeded
    released_inventory_ids: List[int] = []  # Released inventory IDs
    booking_id: Optional[int] = None  # Related booking ID
    status: str  # Result status


# ============================================================
# INVENTORY CONFIRMATION SCHEMAS
# ============================================================

class InventoryConfirmRequest(BaseModel):  # Confirm held inventory
    booking_id: int  # Booking containing held inventory


class InventoryConfirmResponse(BaseModel):  # Inventory confirmation response
    confirmed: bool  # Whether confirmation succeeded
    booking_id: int  # Booking ID
    inventory_ids: List[int]  # Confirmed inventory IDs
    status: str  # Confirmation status


# ============================================================
# BOOKING SCHEMAS
# ============================================================

class BookingCreate(BaseModel):  # Legacy booking creation request
    event_id: int  # Event ID
    tickets: int = Field(gt=0)  # Number of tickets
    idempotency_key: Optional[str] = None  # Duplicate request protection


class BookingItemCreate(BaseModel):  # Booking inventory selection
    inventory_id: int  # Selected inventory ID


class BookingHoldCreate(BaseModel):  # Legacy-compatible booking hold request
    event_id: int  # Event ID
    seat_ids: Optional[List[int]] = None  # Fixed seats
    zone_id: Optional[int] = None  # Zone inventory
    ticket_type_id: Optional[int] = None  # General/pass inventory
    tickets: int = Field(default=1, gt=0)  # Quantity requested
    hold_seconds: int = Field(default=900, ge=60, le=1800)  # Default 15-minute hold
    idempotency_key: Optional[str] = None  # Duplicate request protection


class BookingItemResponse(BaseModel):  # Booking item response
    id: int  # Booking item ID
    booking_id: int  # Booking ID
    inventory_id: int  # Inventory ID
    quantity: int  # Number of inventory units
    price: int  # Price captured at hold time
    status: str  # Item state
    created_at: datetime  # Creation timestamp

    model_config = ConfigDict(from_attributes=True)  # Enable SQLAlchemy ORM conversion


class BookingResponse(BaseModel):  # Booking response
    id: int  # Booking ID
    user_id: int  # User ID
    event_id: int  # Event ID
    tickets: int  # Ticket quantity
    status: str  # Booking lifecycle state
    total_amount: int  # Booking total
    payment_status: str  # Payment state
    idempotency_key: Optional[str] = None  # Idempotency key
    expires_at: Optional[datetime] = None  # Hold expiration
    booking_time: datetime  # Booking timestamp
    items: List[BookingItemResponse] = []  # Booking inventory items

    model_config = ConfigDict(from_attributes=True)  # Enable SQLAlchemy ORM conversion


class BookingCheckout(BaseModel):  # Complete checkout request
    booking_id: int  # Booking being checked out
    payment_method: str = "mock"  # Payment method


class CheckoutCreate(BaseModel):  # Checkout request
    booking_id: int  # Booking being checked out
    method: str = "mock"  # Payment method


class BookingDetailResponse(BaseModel):  # Detailed booking response
    id: int  # Booking ID
    user_id: int  # User ID
    event_id: int  # Event ID
    tickets: int  # Ticket quantity
    status: str  # Booking status
    total_amount: int  # Booking total
    booking_time: datetime  # Booking creation timestamp
    expires_at: Optional[datetime] = None  # Hold expiration
    payment_status: str  # Payment status
    tickets_rel: List["TicketResponse"] = []  # Issued tickets
    items: List[BookingItemResponse] = []  # Inventory items

    model_config = ConfigDict(from_attributes=True)  # Enable SQLAlchemy ORM conversion


# ============================================================
# PAYMENT SCHEMAS
# ============================================================

class PaymentCreate(BaseModel):  # Legacy payment request
    booking_id: int  # Booking ID
    method: str = "mock"  # Payment method


class PaymentResponse(BaseModel):  # Payment response
    id: int  # Payment ID
    booking_id: int  # Booking ID
    user_id: int  # User ID
    user_name: Optional[str] = None  # Compatibility user name
    amount: int  # Payment amount
    status: str  # Payment state
    method: str  # Payment method
    transaction_id: str  # Internal transaction ID
    provider: Optional[str] = None  # Payment provider
    provider_payment_id: Optional[str] = None  # Provider payment ID
    currency: str = "INR"  # Payment currency
    failure_reason: Optional[str] = None  # Payment failure reason
    created_at: datetime  # Payment creation time
    paid_at: Optional[datetime] = None  # Payment completion time

    model_config = ConfigDict(from_attributes=True)  # Enable SQLAlchemy ORM conversion


class PaymentWebhookRequest(BaseModel):  # Payment gateway webhook
    provider: str  # Gateway provider
    provider_payment_id: str  # Provider payment ID
    transaction_id: Optional[str] = None  # Internal transaction ID
    status: str  # Payment status
    webhook_event_id: str  # Unique webhook event ID
    failure_reason: Optional[str] = None  # Failure reason


# ============================================================
# TICKET SCHEMAS
# ============================================================

class TicketResponse(BaseModel):  # Issued ticket response
    id: int  # Ticket ID
    booking_id: int  # Booking ID
    event_id: int  # Event ID
    seat_id: Optional[int] = None  # Seat ID
    zone_id: Optional[int] = None  # Zone ID
    ticket_type_id: Optional[int] = None  # Ticket type ID
    ticket_code: str  # Public ticket code
    qr_token: str  # QR verification token
    price_paid: int  # Actual paid price
    status: str  # Ticket status
    created_at: datetime  # Ticket creation timestamp
    used_at: Optional[datetime] = None  # Ticket usage timestamp

    model_config = ConfigDict(from_attributes=True)  # Enable SQLAlchemy ORM conversion


# ============================================================
# USER / AUTH SCHEMAS
# ============================================================

class UserCreate(BaseModel):  # User registration request
    username: str  # Username
    email: str  # Email address
    password: str  # Password
    role: str = "user"  # User role
    phone: Optional[str] = None  # Optional phone number


class LoginRequest(BaseModel):  # Login request
    identifier: str  # Username or email
    password: str  # Password


class UserResponse(BaseModel):  # User response
    id: int  # User ID
    username: str  # Username
    role: str  # User role
    is_active: bool  # Account state
    email: Optional[str] = None  # Email address
    email_verified: bool  # Email verification state
    phone_verified: bool  # Phone verification state
    profile_image: Optional[str] = None  # Profile image

    model_config = ConfigDict(from_attributes=True)  # Enable SQLAlchemy ORM conversion


class UserProfile(BaseModel):  # User profile response
    id: int  # User ID
    username: str  # Username
    role: str  # User role
    full_name: Optional[str] = None  # Full name
    bio: Optional[str] = None  # Biography
    email: Optional[str] = None  # Email address
    phone: Optional[str] = None  # Decrypted phone
    profile_image: Optional[str] = None  # Profile image
    email_verified: bool  # Email verification state
    phone_verified: bool  # Phone verification state
    bookings: int  # Booking count


class UserProfileUpdate(BaseModel):  # Profile update request
    full_name: Optional[str] = None  # Full name
    bio: Optional[str] = None  # Biography
    profile_image: Optional[str] = None  # Profile image


class ProfileUpdate(UserProfileUpdate):  # Backward-compatible profile update
    pass  # Reuse profile update fields


# ============================================================
# CATEGORY SCHEMAS
# ============================================================

class CategoryBase(BaseModel):  # Category base schema
    name: str  # Category name


class CategoryCreate(CategoryBase):  # Category creation
    pass  # Reuse category base fields


class CategoryResponse(CategoryBase):  # Category response
    id: int  # Category ID

    model_config = ConfigDict(from_attributes=True)  # Enable SQLAlchemy ORM conversion


# ============================================================
# NOTIFICATION SCHEMAS
# ============================================================

class NotificationCreate(BaseModel):  # Notification creation
    message: str  # Notification message
    user_name: Optional[str] = None  # Compatibility user reference


class NotificationBase(BaseModel):  # Notification base
    message: str  # Notification message


class NotificationResponse(NotificationBase):  # Notification response
    id: int  # Notification ID
    created_at: datetime  # Notification creation timestamp

    model_config = ConfigDict(from_attributes=True)  # Enable SQLAlchemy ORM conversion


# ============================================================
# OTP SCHEMAS
# ============================================================

class OTPSendRequest(BaseModel):  # OTP send request
    purpose: str  # OTP purpose
    destination: Optional[str] = None  # Email or phone destination


class OTPVerifyRequest(BaseModel):  # OTP verification request
    purpose: str  # OTP purpose
    otp: str  # OTP code
    destination: Optional[str] = None  # Email or phone destination


class OTPVerifyResponse(BaseModel):  # OTP verification response
    message: str  # Verification result
    verification_token: str  # Temporary verification token


class ChangeUsernameRequest(BaseModel):  # Username change request
    username: str  # New username
    verification_token: str  # Verification token


class ChangeEmailRequest(BaseModel):  # Email change request
    email: str  # New email
    verification_token: str  # Verification token


class ChangePhoneRequest(BaseModel):  # Phone change request
    phone: str  # New phone number
    verification_token: str  # Verification token


class ChangePasswordRequest(BaseModel):  # Password change request
    password: str  # New password
    verification_token: str  # Verification token