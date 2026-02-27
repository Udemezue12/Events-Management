import logging
from typing import List

from core.get_db import get_db_async
from core.require_permissions import (
    require_admin_user,
    require_attendee_organizer_and_admin_user,
    require_organizer_and_admin_user,
)
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from models.models import User
from schemas.schema import (
    EventTicketTypeCreate,
  
)
from services.event_ticket_service import EventTicketService
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(tags=["Event Ticket Type(VIP, REGULAR, VVIP)"], )


@cbv(router)
class EventTicketTypeRoutes:
    def __init__(self, db: AsyncSession = get_db_async()):
        self.event_ticket_type = EventTicketService(db)

    @router.post("/{event_id}/create/ticket_type", dependencies=[rate_limit])
    @safe_handler
    async def reserve_ticket(
        self,
        event_id: int,
        payload: EventTicketTypeCreate,
        current_user: User = Depends(
            require_organizer_and_admin_user),
        _: None = Depends(validate_csrf_dependency),
    ):

        return await self.event_ticket_type.create(payload=payload, current_user=current_user, event_id=event_id)
