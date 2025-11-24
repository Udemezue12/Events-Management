from datetime import timezone

from models.models import Event, Venue
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError


class EventRepo:
    def __init__(self, db):
        self.db = db

    async def create(self, payload, creator_id: int, venue_id: int):
        existing_event = await self.db.execute(
            select(Event).where(
                Event.title == payload.title, Event.venue_id == venue_id
            )
        )
        if existing_event.scalars().first():
            raise ValueError(f"Event '{payload.title}' already exists in this venue")
        start_time_naive = payload.start_time.astimezone(timezone.utc).replace(tzinfo=None)
        end_time_naive = payload.end_time.astimezone(timezone.utc).replace(tzinfo=None)
        event = Event(
            title=payload.title,
            description=payload.description,
            start_time=start_time_naive,
            end_time=end_time_naive,
            total_tickets=payload.total_tickets,
            tickets_sold=0,
            ticket_price=getattr(payload, "ticket_price", 0.0),
            status=getattr(payload, "status", None),
            created_by=creator_id,
            venue_id=venue_id,
        )
        self.db.add(event)
        try:
            await self.db.commit()
            await self.db.refresh(event)
            return event
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_all(self):
        result = await self.db.execute(select(Event))
        return result.scalars().all()

    async def get_by_id(self, event_id: int):
        result = await self.db.execute(select(Event).where(Event.id == event_id))
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
