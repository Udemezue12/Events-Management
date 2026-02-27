from datetime import datetime
from typing import List, Optional, Any

from core.get_db import Base
from geoalchemy2 import Geography
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    CheckConstraint,
    UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.dialects.postgresql import TSRANGE, ExcludeConstraint
from sqlalchemy import Computed, text

from .base import BaseMixin
from .enums import EventStatus, PaymentStatus, Role, TicketType, TicketStatus, PaymentMethod, PDFStatus
from .shape import convert_location


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False)
    last_name: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(
        String(20), unique=True, nullable=True
    )
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False), default=Role.ATTENDEE
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    events_created: Mapped[List["Event"]] = relationship(
        "Event", back_populates="creator", cascade="all, delete-orphan"
    )
    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket", back_populates="user", cascade="all, delete-orphan"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="user", cascade="all, delete-orphan"
    )
    reviews: Mapped[List["Review"]] = relationship(
        "Review", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.hashed_password, password)

    def normalize(self) -> None:
        self.username = self.username.strip().lower()
        self.email = self.email.strip().lower()
        self.first_name = self.first_name.strip().title()
        self.last_name = self.last_name.strip().title()


class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"

    __table_args__ = (
        Index("idx_blacklisted_token", "token"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    token: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
    )

    blacklisted_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class State(Base):
    __tablename__ = "states"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    name: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow()
    )
    location: Mapped[Optional[object]] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True
    )

    venues: Mapped[List["Venue"]] = relationship(
        "Venue", back_populates="state", cascade="all, delete-orphan"
    )

    def __str__(self):
        return self.name

    def as_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "location": convert_location(self.location),
        }


class Venue(Base):
    __tablename__ = "venues"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    image_url: Mapped[str] = mapped_column(String, nullable=True)
    image_hash: Mapped[str] = mapped_column(String, nullable=True)
    public_id: Mapped[str] = mapped_column(String, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)
    is_available: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    location: Mapped[Optional[object]] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True
    )

    events: Mapped[List["Event"]] = relationship(
        "Event", back_populates="venue", cascade="all, delete-orphan"
    )
    state_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("states.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    state: Mapped["State"] = relationship("State", back_populates="venues")

    def __str__(self):
        return self.name

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "capacity": self.capacity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "location": convert_location(self.location),
        }


class Event(Base, BaseMixin):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_tickets: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tickets_sold: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, native_enum=False), default=EventStatus.UPCOMING
    )
    time_range: Mapped[object] = mapped_column(
        TSRANGE,
        Computed("tsrange(start_time, end_time)", persisted=True),
    )

    total_ticket_price: Mapped[Optional[float]] = mapped_column(
        Float,
        default=0.0,
        nullable=True,
    )
    total_ticket_price_sold: Mapped[Optional[float]] = mapped_column(
        Float,
        default=0.0,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    image_url: Mapped[str] = mapped_column(String, nullable=True)
    image_hash: Mapped[str] = mapped_column(String, nullable=True)
    public_id: Mapped[str] = mapped_column(String, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    venue_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("venues.id", ondelete="SET NULL"), nullable=True,
    )

    #
    creator: Mapped["User"] = relationship(
        "User", back_populates="events_created")
    venue: Mapped["Venue"] = relationship(
        "Venue", back_populates="events", foreign_keys=[venue_id])
    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket",
        back_populates="event",
        cascade="all, delete-orphan"
    )
    reviews: Mapped[List["Review"]] = relationship(
        "Review", back_populates="event", cascade="all, delete-orphan"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="event", cascade="all, delete-orphan"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (

        ExcludeConstraint(
            ("venue_id", "="),
            ("time_range", "&&"),
            name="no_overlapping_active_events_per_venue",
            using="gist",
            where=text("is_active = TRUE"),
        ),

        # End time must be after start
        CheckConstraint(
            "end_time > start_time",
            name="check_end_after_start",
        ),

        # Unique title per venue
        UniqueConstraint(
            "title",
            "venue_id",
            name="unique_event_title_per_venue",
        ),
    )


class EventTicketType(Base):
    __tablename__ = "event_ticket_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE")
    )

    ticket_type: Mapped[TicketType] = mapped_column(
        Enum(TicketType, native_enum=False)
    )

    price: Mapped[float] = mapped_column(Float)
    total_price: Mapped[float] = mapped_column(Float, default=0.0)

    total_price_sold: Mapped[float] = mapped_column(Float, default=0.0)
    

    total_quantity: Mapped[int] = mapped_column(Integer)
    total_sold_quantity: Mapped[int] = mapped_column(
        Integer, default=0, nullable=True)
    total_reserved_quantity: Mapped[int] = mapped_column(
        Integer, default=0, nullable=True
    )
    

    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket", back_populates="ticket_type")
    event: Mapped["Event"] = relationship(
        "Event", back_populates="ticket_types")

    @property
    def available_quantity(self):
        return self.total_quantity - self.total_sold_quantity

    @property
    def check_price_balance(self):
        return self.total_price - self.total_price_sold


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id", ondelete="CASCADE")
    )

    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, native_enum=False), default=TicketStatus.PENDING
    )
    price_paid: Mapped[float] = mapped_column(Float, default=0.0, nullable=True)
    ticket_type_id: Mapped[int] = mapped_column(
        ForeignKey("event_ticket_types.id")
    )
    total_ticket_quantity:Mapped[int]= mapped_column(Integer, nullable=True, index=True)
    ticket_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=True
    )
    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    barcode: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pdf_status: Mapped[PDFStatus] = mapped_column(
        Enum(PDFStatus, native_enum=False),
        nullable=False,
        index=True,
        default=PDFStatus.PENDING,
    )

    ticket_pass_url: Mapped[Optional[str]
                            ] = mapped_column(String, nullable=True)
    ticket_pass_public_id: Mapped[Optional[str]
                                  ] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    ticket_type: Mapped["EventTicketType"] = relationship(
        "EventTicketType", back_populates="tickets", cascade="all, delete"
    )

    event: Mapped["Event"] = relationship("Event", back_populates="tickets")
    user: Mapped["User"] = relationship("User", back_populates="tickets")
    payment: Mapped["Payment"] = relationship(
        "Payment", back_populates="tickets", uselist=False
    )
    checked_in_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    checked_in_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    

    def as_dict(self):
        return {
            "id": self.id,
            "user_name": f"{self.user.first_name} {self.user.last_name}" if self.user else None,
            "user_email": self.user.email if self.user else None,
            "event_name": self.event.title if self.event else None,
            "type": self.ticket_types.type.value if self.ticket_types else None,
            "unit_price": self.ticket_types.price if self.ticket_types else None,
            "total_price": self.price_paid,
            "status": self.status,
            "price_paid": self.price_paid,
            "venue_name": self.event.venue.name
            if self.event and self.event.venue
            else None,
            "quantity": self.total_ticket_quantity,
        }


class Payment(Base, BaseMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    total_amount: Mapped[float] = mapped_column(Float, nullable=True)
    ticket_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False),
        default=PaymentStatus.PENDING,
        index=True
    )

    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, native_enum=False),
        nullable=False,
        default=PaymentMethod.NONE_YET
    )
    

    reference: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        index=True,
        nullable=False
    )

    transaction_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now()
    )

    # 🔥 Relationships
    user: Mapped["User"] = relationship("User", back_populates="payments")
    event: Mapped["Event"] = relationship("Event", back_populates="payments")

    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket",
        back_populates="payment",
        cascade="all"
    )

    items: Mapped[List["PaymentItem"]] = relationship(
        "PaymentItem",
        back_populates="payment",
        cascade="all, delete-orphan"
    )

class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    event: Mapped["Event"] = relationship("Event", back_populates="reviews")
    user: Mapped["User"] = relationship("User", back_populates="reviews")

    def as_dict(self, user: "User", event: "Event"):
        return {
            "id": self.id,
            "event_id": self.event_id,
            "event_name": event.title,
            "user_name": f"{user.last_name} {user.first_name}",
            "user_id": self.user_id,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PaymentItem(Base):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    ticket_type_id: Mapped[int] = mapped_column(
        ForeignKey("event_ticket_types.id"),
        nullable=False
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    unit_price: Mapped[float] = mapped_column(Float, nullable=False)

    total_price: Mapped[float] = mapped_column(Float, nullable=False)

    payment: Mapped["Payment"] = relationship("Payment", back_populates="items")
    ticket_type: Mapped["EventTicketType"] = relationship("EventTicketType")
