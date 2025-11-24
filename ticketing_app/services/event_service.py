from asyncio import create_task as asyncio_task

from core.breaker import breaker
from core.cache import cache
from core.utils import publish_event
from models.models import User
from repositories.event_repo import EventRepo
from schemas.schema import EventOut


class EventService:
    def __init__(self, db):
        self.repository: EventRepo = EventRepo(db)

    async def create_event(self, user: User, payload):
        async def handler():
            if user.role.name not in ["admin", "organizer"]:
                raise PermissionError("Not Permitted")
            event = await self.repository.create(
                payload,
                creator_id=user.id,
                venue_id=payload.venue_id,
            )

            asyncio_task(cache.set_json("events:list:stale", {"stale": True}))

            await asyncio_task(
                
                publish_event(
                    "event.created",
                    {
                        "event_id": event.id,
                        "title": event.title,
                        "start_time": event.start_time.isoformat(),
                        "end_time": event.end_time.isoformat(),
                        "created_at": event.created_at.isoformat(),
                    },
                ),
            )

            return EventOut(**event.as_dict())

        return await breaker.call(handler)

    async def list_events(self):
        async def handler():
            cache_key = "events:list"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached

            events = await self.repository.get_all()
            events_out = [EventOut.from_orm(e).model_dump(mode="json") for e in events]
            await cache.set_json(cache_key, events_out, ttl=120)
            return events_out

        return await breaker.call(handler)

    async def nearby_events(self, lat: float, lon: float):
        async def handler():
            cache_key = f"for-you:{lat}:{lon}"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached

            events = await self.repository.get_nearby(lat, lon)
            events_out = [EventOut.from_orm(e).model_dump(mode="json") for e in events]
            await cache.set_json(cache_key, events_out, ttl=180)
            return events_out

        return await breaker.call(handler)
