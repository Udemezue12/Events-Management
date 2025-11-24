import logging
from typing import List

from core.breaker import breaker
from core.get_current_user import get_current_user
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency

from fastapi import APIRouter, Depends, HTTPException
from fastapi_utils.cbv import cbv
from models.models import User
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
        self,
        data: EventCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        async def handler():
            if current_user.role.name not in ["admin", "organizer"]:
                raise HTTPException(status_code=403, detail="Not permitted")
            return await EventService(db).create_event(current_user, data)

        return await breaker.call(handler)

    @router.get("/events", response_model=List[EventOut], dependencies=[rate_limit])
    @safe_handler
    async def list_events(
        self,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        async def handler():
            events = await EventService(db).list_events()
            if not events:
                raise HTTPException(status_code=404, detail="No Events Found")
            return events

        return await breaker.call(handler)

    @router.get("/for-you/", response_model=List[EventOut], dependencies=[rate_limit])
    @safe_handler
    async def for_you(
        self,
        lat: float,
        lon: float,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        async def handler():
            nearby_events = await EventService(db).nearby_events(lat, lon)
            if not nearby_events:
                raise HTTPException(status_code=404, detail="No Events Found")
            return nearby_events

        return await breaker.call(handler)
