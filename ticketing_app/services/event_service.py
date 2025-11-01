
from asyncio import create_task as asyncio_task
from asyncio import run as asyncio_run
from datetime import datetime

from core.cache import cache
from core.threads import run_in_thread
from core.utils import publish_event
from repositories.event_repo import EventRepo
from schemas.schema import EventOut


class EventService:
    def __init__(self, repository: EventRepo):
        self.repository = repository

    async def create_event(self, db, payload):
        await self.repository.create(db, payload)

        asyncio_task(cache.set_json("events:list:stale", {"stale": True}))

        await run_in_thread(
            asyncio_run,
            publish_event(
                "event.created",
                {
                    "title": payload.title,
                    "description": payload.description,
                    "start_time": payload.start_time.isoformat(),
                    "end_time": payload.end_time.isoformat(),
                    "total_tickets": payload.total_tickets,
                    "venue_address": payload.venue_address,
                    "venue_lat": payload.venue_lat,
                    "venue_lon": payload.venue_lon,
                    "created_at": datetime.utcnow().isoformat(),
                },
            ),
        )

        return EventOut(
            id=payload.id,
            title=payload.title,
            description=payload.description,
            start_time=payload.start_time,
            end_time=payload.end_time,
            total_tickets=payload.total_tickets,
            tickets_sold=0,
            venue_address=payload.venue_address,
            venue_lat=payload.venue_lat,
            venue_lon=payload.venue_lon,
        )

    async def list_events(self, db):
        cache_key = "events:list"
        cached = await cache.get_json(cache_key)
        if cached:
            return cached

        events = await self.repository.get_all(db)
        await cache.set_json(cache_key, [e.as_dict() for e in events], ttl=120)
        return events

    async def nearby_events(self, db, lat: float, lon: float):
        cache_key = f"for-you:{lat}:{lon}"
        cached = await cache.get_json(cache_key)
        if cached:
            return cached

        events = await self.repository.get_nearby(db, lat, lon)
        await cache.set_json(cache_key, [e.as_dict() for e in events], ttl=180)
        return events
