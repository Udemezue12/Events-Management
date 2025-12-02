from datetime import datetime
from typing import List, Optional

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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .base import BaseMixin
from .enums import EventStatus, PaymentStatus, Role, TicketType
from .shape import convert_location


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    last_name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(
        String(20), unique=True, nullable=True
    )
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False), default=Role.attendee
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
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
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    token: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    blacklisted_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    __table_args__ = (Index("idx_blacklisted_token", "token"),)


class Venue(Base):
    __tablename__ = "venues"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
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
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_tickets: Mapped[int] = mapped_column(Integer, nullable=False)
    tickets_sold: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, native_enum=False), default=EventStatus.upcoming
    )
    ticket_price: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    venue_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("venues.id", ondelete="SET NULL"), nullable=True
    )

    #
    creator: Mapped["User"] = relationship("User", back_populates="events_created")
    venue: Mapped["Venue"] = relationship("Venue", back_populates="events")
    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket", back_populates="event", cascade="all, delete-orphan"
    )
    reviews: Mapped[List["Review"]] = relationship(
        "Review", back_populates="event", cascade="all, delete-orphan"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="event", cascade="all, delete-orphan"
    )


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
    type: Mapped[TicketType] = mapped_column(
        Enum(TicketType, native_enum=False), default=TicketType.regular
    )
    status: Mapped[str] = mapped_column(String, default="reserved")
    price_paid: Mapped[float] = mapped_column(Float, default=0.0)
    qr_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    event: Mapped["Event"] = relationship("Event", back_populates="tickets")
    user: Mapped["User"] = relationship("User", back_populates="tickets")
    payment: Mapped["Payment"] = relationship(
        "Payment", back_populates="ticket", uselist=False
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    def as_dict(self):
        return {
            "id": self.id,
            "user_name": f"{self.user.first_name} {self.user.last_name}" if self.user else None,
            "user_email": self.user.email if self.user else None,
            "event_name": self.event.title if self.event else None,
            "type": self.type.value,
            "status": self.status,
            "price_paid": self.price_paid,
            "venue_name": self.event.venue.name
            if self.event and self.event.venue
            else None,
            "quantity": self.quantity,
        }


class Payment(Base, BaseMixin):
    __tablename__ = "payments"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE")
    )
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False), default=PaymentStatus.pending
    )
    ticket_quantity: Mapped[int] = mapped_column(Integer, default=1)
    payment_method: Mapped[str] = mapped_column(String, default="card")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reference: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="payment")
    user: Mapped["User"] = relationship("User", back_populates="payments")
    event: Mapped["Event"] = relationship("Event", back_populates="payments")

    def as_dict(self, include_ids: bool = False):
        event = self.event or (self.ticket.event if self.ticket else None)
        name = f"{self.user.first_name} {self.user.last_name}" if self.user else None
        data = {
            "id": self.id,
            "user_name": name,
            "status": self.status.value if self.status else None,
            "ticket_quantity": self.ticket_quantity,
            "event_name": event.title if event else None,
            "event_creator": f"{event.creator.first_name} {event.creator.last_name}" if event and event.creator else None,
            "venue": event.venue.name if event and event.venue else None,  # rename key
            "amount": self.amount,
            "payment_method": self.payment_method,
            "created_at": self.created_at.isoformat()
            if include_ids
            else self.created_at.isoformat(),
            "reference": self.reference,
        }

        if include_ids:
            data.update(
                {
                    "ticket_id": self.ticket.id if self.ticket else None,
                    "event_id": event.id if event else None,
                }
            )

        return data


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
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
