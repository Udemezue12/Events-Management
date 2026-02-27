
import uuid
from datetime import datetime, timezone
from pathlib import Path

from core.cache import cache
from core.json_response import SerializeResponse
from core.mapper import ORMMapper
from core.paginate import PaginatePage
from core.utils import publish_event
from fastapi import HTTPException
from models.enums import EventStatus
from repositories.event_repo import EventRepo
from schemas.schema import EventBaseOut, EventOut
from worker.celery_app import app as task_app

UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class EventService:
    def __init__(self, db):
        self.repository: EventRepo = EventRepo(db)
        self.mapper: ORMMapper = ORMMapper()
        self.json_response: SerializeResponse = SerializeResponse()
        self.paginate: PaginatePage = PaginatePage()

    async def cancel_event(self, event_id: int, current_user):
        event = await self.repository.set_isActive(event_id, is_active=False)
        if not event:
            raise HTTPException(404, "Event not found")
        if event.created_by != current_user.id:
            raise HTTPException(400, "Not Allowed")
        

        task_app.send_task(
            "process_event_refunds",
            args=[str(event_id)],
        )

        return {"message": "Event cancelled. Refunds processing."}

    async def create_event(self, venue_id: int, current_user, payload, files: list,):
        now = datetime.utcnow()
        saved_paths = []

        for file in files:
            unique_name = f"{uuid.uuid4()}{Path(file.filename).suffix}"
            file_path = UPLOAD_DIR / unique_name

            with file_path.open("wb") as buffer:
                buffer.write(await file.read())

            saved_paths.append(str(file_path))

        if payload.start_time <= now:
            raise HTTPException(
                status_code=400,
                detail="Cannot create event in the past."
            )

        if payload.end_time <= payload.start_time:
            raise HTTPException(
                status_code=400,
                detail="End time must be after start time."
            )

        start_time_naive = payload.start_time.astimezone(
            timezone.utc).replace(tzinfo=None)
        end_time_naive = payload.end_time.astimezone(
            timezone.utc).replace(tzinfo=None)
        if await self.repository.check_conflict(
            venue_id=venue_id,
            start_time_naive=start_time_naive,
            end_time_naive=end_time_naive


        ):
            raise HTTPException(
                status_code=400,
                detail="Venue already booked for this time."
            )

        event = await self.repository.create(
            title=payload.title,
            description=payload.title,
            start_time_naive=start_time_naive,
            end_time_naive=end_time_naive,
            total_tickets=payload.total_tickets,
            status=EventStatus.UPCOMING,
            user_id=current_user.id,
            venue_id=venue_id,
        )
        task_app.send_task("sync_upload_event_images", args=[
            str(event.created_by),
            str(event.id),
            saved_paths,
        ],
        )

        await cache.delete_cache_keys_async(
            "events:list",
            f"for-you:{payload.latitude}:{payload.longitude}"
        )

        await publish_event(
            "event.created",
            {
                "event_id": event.id,
                "title": event.title,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat(),
                "created_at": event.created_at.isoformat(),
            },
        )

        return EventOut(**event.as_dict())

    async def list_events(self, page: int = 1, per_page: int = 20):

        cache_key = "events:list::{page}:{per_page}"
        cached = await cache.async_get_json(cache_key)
        if cached:
            return self.mapper.many(items=cached, schema=EventBaseOut)

        events = await self.repository.get_all(page=page, per_page=per_page)
        events_out = self.mapper.many(items=events, schema=EventBaseOut)
        if not events_out:
            return []
        paginated = self.paginate.paginate(events_out, page, per_page)

        await cache.async_set_json(cache_key, self.json_response.get_list_json_dumps(paginated), ttl=120)
        return paginated

    async def nearby_events(self, lat: float, lon: float):

        cache_key = f"for-you:{lat}:{lon}"
        cached = await cache.async_get_json(cache_key)
        if cached:
            return cached

        events = await self.repository.get_nearby(lat, lon)
        events_out = [EventOut.from_orm(e).model_dump(
            mode="json") for e in events]
        if not events_out:
            return []
        await cache.async_set_json(cache_key, events_out, ttl=180)
        return events_out
