from core.get_db import Base
from geoalchemy2 import Geography
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    total_tickets = Column(Integer, nullable=False)
    tickets_sold = Column(Integer, default=0)
    venue_address = Column(String)

    venue_location = Column(Geography(geometry_type="POINT", srid=4326))
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"))
    status = Column(String, default="reserved")
    created_at = Column(DateTime, server_default=func.now())
