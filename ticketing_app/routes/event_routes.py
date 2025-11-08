import logging

from core.breaker import breaker
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from schemas.schema import EventCreate, EventOut
from services.event_service import EventService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Events"])


@cbv(router)
class EventRoutes:
    @router.post("/events/create", response_model=EventOut, dependencies=[rate_limit])
    @safe_handler
    async def create_event(
        self, data: EventCreate, db: AsyncSession = Depends(get_db_async)
    ):
        async def handler():
            return await EventService(db).create_event(data)

        return await breaker.call(handler)

    @router.get("/events", response_model=list[EventOut], dependencies=[rate_limit])
    @safe_handler
    async def list_events(self, db: AsyncSession = Depends(get_db_async)):
        async def handler():
            return await EventService(db).list_events()

        return await breaker.call(handler)

    @router.get("/for-you/", response_model=list[EventOut], dependencies=[rate_limit])
    @safe_handler
    async def for_you(
        self, lat: float, lon: float, db: AsyncSession = Depends(get_db_async)
    ):
        async def handler():
            return await EventService(db).nearby_events(lat, lon)

        return await breaker.call(handler)
