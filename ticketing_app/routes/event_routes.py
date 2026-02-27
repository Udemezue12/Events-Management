import logging
from typing import List

from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency

from fastapi import APIRouter, Depends, File, UploadFile
from core.require_permissions import require_organizer_and_admin_user,  require_attendee_organizer_and_admin_user
from fastapi_utils.cbv import cbv
from models.models import User
from schemas.schema import EventCreate, EventOut
from services.event_service import EventService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Events"])


@cbv(router)
class EventRoutes:
    @router.post("/{event_id}/cancel", response_model=EventOut, dependencies=[rate_limit])
    @safe_handler
    async def cancel_event(
        self,
        event_id: int,
        current_user: User = Depends(require_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):

        return await EventService(db).cancel_event(current_user=current_user, event_id=event_id)

    @router.post("/events/create", response_model=EventOut, dependencies=[rate_limit])
    @safe_handler
    async def create_event(
        self,
        data: EventCreate,
        files: list[UploadFile] = File(...),

        current_user: User = Depends(require_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):

        return await EventService(db).create_event(current_user, data, files)

    @router.get("/events", response_model=List[EventOut], dependencies=[rate_limit])
    @safe_handler
    async def list_events(
        self,
        current_user: User = Depends(
            require_attendee_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):

        return await EventService(db).list_events()

    @router.get("/for-you/", response_model=List[EventOut], dependencies=[rate_limit])
    @safe_handler
    async def for_you(
        self,
        lat: float,
        lon: float,
        current_user: User = Depends(
            require_attendee_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):

        return await EventService(db).nearby_events(lat, lon)
