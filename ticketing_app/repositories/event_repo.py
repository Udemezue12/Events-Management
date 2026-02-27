from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from models.enums import EventStatus
from models.models import Event, Venue
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload


class EventRepo:
    def __init__(self, db):
        self.db = db

    async def increment_event_tickets_sold(
        self,
        event_id: int,
        quantity: int
    ) -> Event:

        

            stmt = (
                update(Event)
                .where(Event.id == event_id)
                .values(
                    tickets_sold=Event.total_tickets_sold + quantity
                )
                .returning(Event)
            )

            result = await self.db.execute(stmt)
            event = result.scalar_one_or_none()

            if not event:
                raise ValueError("Event not found")

            return event
    def sync_increment_event_tickets_sold(
        self,
        event_id: int,
        quantity: int
    ) -> Event:

        

            stmt = (
                update(Event)
                .where(Event.id == event_id)
                .values(
                    tickets_sold=Event.total_tickets_sold + quantity
                )
                .returning(Event)
            )

            result = elf.db.execute(stmt)
            event = result.scalar_one_or_none()

            if not event:
                raise ValueError("Event not found")

            return event
    async def set_isActive(
        self,
        event_id: int,
        is_active:bool=False
    ) -> Event:

        async with self.db.begin():

            stmt = (
                update(Event)
                .where(Event.id == event_id)
                .values(
                    is_active=is_active
                )
                .returning(Event)
            )

            result = await self.db.execute(stmt)
            event = result.scalar_one_or_none()

            if not event:
                raise ValueError("Event not found")

        return event

    async def get_event_by_id(self, event_id: int) -> Event:
        return await self.db.scalar(select(Event).where(Event.id == event_id))

    def sync_get_by_hash(self, event_id: int, image_hash: str) -> Optional[Event]:
        result = self.db.execute(select(Event).where(
            Event.id == event_id, Event.image_hash == image_hash))
        return result.scalar_one_or_none()

    def count_user_uploads_between(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
    ) -> Event:
        if start.tzinfo is not None:
            start = start.replace(tzinfo=None)

        if end.tzinfo is not None:
            end = end.replace(tzinfo=None)
        stmt = (
            select(func.count(Event.id))
            .where(Event.created_by == user_id)
            .where(Event.uploaded_at >= start)
            .where(Event.uploaded_at < end)
        )
        result = self.db.execute(stmt)
        return result.scalar_one()

    async def check_conflict(self, venue_id: int, end_time_naive: datetime, start_time_naive: datetime, is_active: bool = True):
        conflict_query = await self.db.execute(
            select(Event).where(
                Event.venue_id == venue_id,
                Event.start_time < end_time_naive,
                Event.end_time > start_time_naive,
                Event.is_active == is_active
            )
        )
        return conflict_query.scalars().first()

    async def create(self, title: str, description: str, start_time_naive: datetime, end_time_naive: datetime, total_tickets: int, status: EventStatus,  user_id: int, venue_id: int):

        event = Event(
            title=title,
            description=description,
            start_time=start_time_naive,
            end_time=end_time_naive,
            total_tickets=total_tickets,
            tickets_sold=0,
            status=status,
            created_by=user_id,
            venue_id=venue_id,
        )
        self.db.add(event)
        try:
            await self.db.commit()
            await self.db.refresh(event)
            return event
        except IntegrityError as e:
            await self.db.rollback()
            error_msg = str(e.orig)

            if "no_overlapping_events_per_venue" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail="Venue already booked for this time."
                )

            if "unique_event_title_per_venue" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail="An event with this title already exists at this venue."
                )

            if "check_end_after_start" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail="End time must be after start time."
                )

            raise HTTPException(
                status_code=400,
                detail="Invalid event data."
            )

    async def get_all(self, page: int = 1, per_page: int = 20) -> list[Event]:
        offset = (page - 1) * per_page
        result = await self.db.execute(
            select(Event).
            options(
                selectinload(Event.venue),
                selectinload(Event.creator),
                selectinload(Event.tickets),
                selectinload(Event.reviews))
            .order_by(Event.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        return result.scalars().all()

    async def get_by_id(self, event_id: int)->Optional[Event]:
        result = await self.db.execute(select(Event).where(Event.id == event_id).with_for_update())
        return result.scalar_one_or_none()

    async def get_nearby(self, lat: float, lon: float, radius: float = 10_000):
        stmt = (
            select(Event)
            .join(Venue)
            .where(
                func.ST_DWithin(
                    Venue.location,
                    func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326),
                    radius,
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    def sync_upload_venue_image(self, user_id: int, event_id: int, image_hash: str, image_url: str, public_id: str):
        stmt = (
            update(Event)
            .where(
                Event.id == event_id,
                Event.created_by == user_id,

            )
            .values(image_hash=image_hash, image_url=image_url, public_id=public_id)
            .returning(Venue)
        )

        try:
            self.db.execute(stmt)
            self.db.commit()

        except SQLAlchemyError:
            self.db.rollback()
            raise

    def sync_upload_event_image(self, user_id: int, event_id: int, image_hash: str, image_url: str, public_id: str):
        stmt = (
            update(Event)
            .where(
                Event.id == event_id,
                Event.created_by == user_id,

            )
            .values(image_hash=image_hash, image_url=image_url, public_id=public_id)
            .returning(Event)
        )

        try:
            self.db.execute(stmt)
            self.db.commit()

        except SQLAlchemyError:
            self.db.rollback()
            raise
