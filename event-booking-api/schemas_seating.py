from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List
from datetime import datetime


class LayoutCreate(BaseModel):                                                               # VENUE LAYOUT CREATION SCHEMA
    event_id: int = Field(gt=0)                                                              # EVENT ID FOR THE VENUE LAYOUT
    name: str = Field(min_length=1, max_length=100)                                          # HUMAN-READABLE LAYOUT NAME


class ZoneCreate(BaseModel):                                                                 # EVENT ZONE CREATION SCHEMA
    name: str = Field(min_length=1, max_length=100)                                          # ZONE NAME SUCH AS VIP, PREMIUM OR GENERAL
    code: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")              # SAFE UNIQUE ZONE CODE
    zone_type: str = Field(default="seated", pattern=r"^(seated|general)$")                  # SUPPORTED INVENTORY ZONE TYPE
    capacity: int = Field(default=0, ge=0, le=1000000)                                       # MAXIMUM CAPACITY OF THE ZONE
    base_price: int = Field(default=0, ge=0, le=100000000)                                   # DEFAULT SERVER-SIDE PRICE FOR THE ZONE


class RowCreate(BaseModel):                                                                  # SEAT ROW GENERATION SCHEMA
    zone_id: int = Field(gt=0)                                                               # PARENT ZONE ID
    row_label: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9_-]+$")         # SAFE ROW LABEL SUCH AS A, B OR VIP-A
    seat_count: int = Field(gt=0, le=500)                                                    # NUMBER OF SEATS TO GENERATE IN THE ROW
    starting_price: int = Field(default=0, ge=0, le=100000000)                               # STARTING PRICE FOR GENERATED SEATS


class SeatResponse(BaseModel):                                                               # PUBLIC SEAT RESPONSE SCHEMA
    model_config = ConfigDict(from_attributes=True)                                          # ALLOW SQLALCHEMY MODEL SERIALIZATION
    id: int = Field(gt=0)                                                                    # UNIQUE DATABASE SEAT ID
    seat_code: str = Field(min_length=1, max_length=100)                                     # UNIQUE HUMAN-READABLE SEAT CODE
    seat_number: int = Field(gt=0)                                                           # NUMERIC SEAT NUMBER WITHIN THE ROW
    status: str = Field(pattern=r"^(available|locked|sold)$")                                # CURRENT INVENTORY STATE
    price: int = Field(ge=0)                                                                 # CURRENT SERVER-CONTROLLED SEAT PRICE


class SeatHoldRequest(BaseModel):                                                            # TEMPORARY SEAT LOCK REQUEST
    seat_ids: List[int] = Field(min_length=1, max_length=10)                                 # SEATS REQUESTED FOR TEMPORARY LOCKING

    @field_validator("seat_ids")                                                            # VALIDATE REQUESTED SEAT IDS
    @classmethod
    def validate_seat_ids(cls, value: List[int]) -> List[int]:                               # VALIDATE POSITIVE UNIQUE IDS
        if any(seat_id <= 0 for seat_id in value):                                           # REJECT INVALID DATABASE IDS
            raise ValueError("Seat IDs must be positive integers")                           # RETURN VALIDATION ERROR
        if len(set(value)) != len(value):                                                    # PREVENT DUPLICATE SEAT IDS
            raise ValueError("Duplicate seat IDs are not allowed")                           # RETURN VALIDATION ERROR
        return value                                                                          # RETURN VALIDATED SEAT IDS


class SeatHoldResponse(BaseModel):                                                           # TEMPORARY SEAT LOCK RESPONSE
    lock_token: str = Field(min_length=32, max_length=256)                                   # SECURE TOKEN IDENTIFYING THE ACTIVE SEAT LOCK
    expires_at: datetime                                                                     # UTC LOCK EXPIRATION TIMESTAMP
    seats: List[int] = Field(min_length=1, max_length=10)                                    # SEAT IDS SUCCESSFULLY LOCKED


class ConfirmSeatBookingRequest(BaseModel):                                                  # SEAT BOOKING CONFIRMATION REQUEST
    lock_token: str = Field(min_length=32, max_length=256)                                   # ACTIVE USER-OWNED LOCK TOKEN USED TO CONFIRM BOOKING