import re
from datetime import datetime
from typing import Literal, Optional

import phonenumbers
from models.enums import Role, PaymentMethod, TicketType
from models.models import Event
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class UserBase(BaseModel):
    email: EmailStr
    username: str
    role: Role


class UserCreate(UserBase):
    first_name: str = Field(..., min_length=5)
    last_name: str = Field(..., min_length=5)
    username: str = Field(..., min_length=5, max_length=20)
    password: str = Field(
        ..., min_length=7, json_schema_extra={"type": "string", "format": "password"}
    )
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str):
        try:
            parsed = phonenumbers.parse(value, None)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError(
                    "Invalid phone number. Use full international format.")
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
        except Exception:
            raise ValueError(
                "Invalid phone number format. Use e.g. +2348012345678")

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def capitalize_names(cls, value: str):
        return value.strip().title()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str):
        errors = []
        if len(v) < 7:
            errors.append("≥7 characters")
        if not re.search(r"[A-Z]", v):
            errors.append("uppercase letter")
        if not re.search(r"[a-z]", v):
            errors.append("lowercase letter")
        if not re.search(r"\d", v):
            errors.append("number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            errors.append("special character")
        if errors:
            raise ValueError("Password must contain: " + ", ".join(errors))
        return v

    @model_validator(mode="after")
    def finalize_fields(self):
        if not self.username:
            object.__setattr__(self, "username", self.email.split("@")[0])
        # object.__setattr__(self, "name", f"{self.firstName} {self.lastName}".strip())
        return self


class UserLoginInput(BaseModel):
    email: EmailStr
    password: str = Field(
        ..., min_length=7, json_schema_extra={"type": "string", "format": "password"}
    )


class ForgotPasswordSchema(BaseModel):
    email: EmailStr


class ResetPasswordSchema(BaseModel):
    token: Optional[str] = None
    otp: Optional[str] = None
    new_password: str

    @model_validator(mode="before")
    @classmethod
    def validate_token_or_otp(cls, values):
        token = values.get("token")
        otp = values.get("otp")
        if not token and not otp:
            raise ValueError("Either token or otp must be provided")
        return values


class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    total_tickets: int
    venue_id: int

    ticket_price: Optional[float] = 0.0

    @model_validator(mode="after")
    def validate_event(self):
        if self.total_tickets <= 0:
            raise ValueError("Total tickets must be greater than 0.")

        if self.ticket_price is not None and self.ticket_price < 0:
            raise ValueError("Ticket price cannot be negative.")

        if self.end_time <= self.start_time:
            raise ValueError("Event end_time must be after start_time.")

        if self.start_time < datetime.utcnow():
            raise ValueError("Event cannot start in the past.")

        return self


class EventBaseOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    venue_id: Optional[int]
    created_by: Optional[int]


class EventOut(BaseModel):
    """Output schema for Event data."""
    id: int
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    venue_id: Optional[int]
    created_by: Optional[int]

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, event: Event):
        return cls(
            id=event.id,
            title=event.title,
            description=event.description,
            start_time=event.start_time,
            end_time=event.end_time,
            venue_id=event.venue_id,
            created_by=event.created_by,
        )


class TicketOut(BaseModel):
    id: int
    user_name: str
    user_email: str
    event_name: str
    venue_name: str
    status: str
    type: str
    price_paid: float
    quantity: int

    class Config:
        form_attributes = True


class TicketCreate(BaseModel):
    event_id: int
    quantity: int = Field(1, gt=0)


class MarkTicket(BaseModel):
    ticket_id: int


class GetSingleUserTicket(BaseModel):
    user_id: int


class GetAllUsersTickets(BaseModel):
    event_id: int
    organizer_id: int


class GetOrganizerTickets(BaseModel):
    organizer_id: int


class UsersPaymentOut(BaseModel):
    user_name: Optional[str]
    status: Optional[str]
    ticket_quantity: int
    event_name: Optional[str]
    event_creator: Optional[str]
    venue: Optional[str]
    amount: float
    payment_method: Literal["paystack", "flutterwave"]
    created_at: str
    reference: Optional[str]

    class Config:
        from_attributes = True


class OrganizerPaymentOut(BaseModel):
    ticket_id: int
    event_id: int
    user_name: Optional[str]
    ticket_quantity: int
    event_name: Optional[str]
    event_creator: Optional[str]
    venue: Optional[str]
    amount: float
    status: Optional[str]
    payment_method: Literal["paystack", "flutterwave"]
    reference: Optional[str]
    created_at: datetime

    class Config:
        form_attributes = True


class PaymentRefundOut(BaseModel):
    payment_id: int
    status: Literal["refunded"]


class PaymentRefund(BaseModel):
    payment_id: int


class PaymentInit(BaseModel):
    ticket_id: int

    method: PaymentMethod


class PaymentVerifyOut(BaseModel):
    payment_id: int
    status: Literal["completed", "failed", "pending"]


class PaymentVerify(BaseModel):
    reference: str


class PaymentInitOut(BaseModel):
    payment_id: int
    authorization_url: str
    reference: str


class ReviewCreate(BaseModel):
    event_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=500)


class ReviewOut(BaseModel):
    id: int
    event_id: int
    user_id: int
    event_name: str
    user_name: str
    rating: int
    comment: Optional[str]
    created_at: datetime

    class Config:
        form_attributes = True


class StateBaseSchema(BaseModel):
    name: str
    model_config = {"from_attributes": True}


class StateSchema(StateBaseSchema):
    id: int
    location: Optional[dict] = None
    venues: list["VenueOut"] = Field(default_factory=list)
    model_config = {"from_attributes": True}


class VenueCreate(BaseModel):
    name: str
    address: str
    capacity: int
    state_id:int
    
    # location: Optional[str] = None

    @field_validator("name",  "address", mode="before")
    @classmethod
    def capitalize_names(cls, value: str):
        return value.strip().title()

    @field_validator("capacity", mode="before")
    @classmethod
    def validate_capacity(cls, v: int):
        if v <= 500:
            raise ValueError("Capacity must be greater than 500")
        if v >= 50_000_00:
            raise ValueError("Capacity limit exceeded")

        return v


class VenueUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    capacity: Optional[int] = None
    state_id: Optional[int] = None

    @field_validator("name",  "address", mode="before")
    @classmethod
    def capitalize_names(cls, value: str):
        if value is not None:
         return value.strip().title()

    @field_validator("capacity", mode="before")
    @classmethod
    def validate_capacity(cls, v: int):
        if v is not None:
            if v <= 500:
                raise ValueError("Capacity must be greater than 500")
            if v >= 50_000_00:
                raise ValueError("Capacity limit exceeded")

        return v



class VenueOut(BaseModel):
    id: int
    name: str
    address: str
    capacity: int
    location: Optional[dict]
    location: Optional[dict] = None
    events: list["EventBaseOut"] = Field(default_factory=list)
    model_config = {"from_attributes": True}


class PaymentOutS(BaseModel):
    id: int
    user_id: int
    ticket_id: int
    event_id: int
    amount: float
    payment_method: str
    status: str
    reference: Optional[str]
    created_at: datetime

    class Config:
        form_attributes = True


class TicketOutS(BaseModel):
    id: int
    user_id: int
    event_id: int
    status: str
    created_at: datetime

    class Config:
        form_attributes = True


class EventTicketTypeCreate(BaseModel):
    ticket_type:TicketType
    total_quantity:int
    price:float


