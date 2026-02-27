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
    TicketCreate,
    TicketOut,
)
from services.ticket_service import TicketService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Tickets"])


@cbv(router)
class TicketsRoutes:
    @router.post("/{event_id}/reserve/ticket", dependencies=[rate_limit], response_model=TicketOut)
    @safe_handler
    async def reserve_ticket(
        self,
        event_id: int,
        data: TicketCreate,
        current_user: User = Depends(
            require_attendee_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):

        return await TicketService(db).reserve_ticket(
            user_id=current_user.id,
            event_id=event_id,
            quantity=data.quantity,
        )
    
    @router.get(
        "/{user_id}/history/tickets",
        dependencies=[rate_limit],
        response_model=List[TicketOut],
    )
    @safe_handler
    async def get_user_tickets(
        self,
        page: int = 1,
        per_page: int = 20,
        current_user: User = Depends(
            require_attendee_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await TicketService(db).get_user_ticket(
            user_id=current_user.id, page=page, per_page=per_page
        )

    @router.get(
        "/all/tickets", dependencies=[rate_limit], response_model=list[TicketOut]
    )
    @safe_handler
    async def get_all_user_tickets(
        self,
        event_id: int | None = None,
        organizer_id: int | None = None,
        page: int = 1,
        per_page: int = 20,
        current_user: User = Depends(require_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await TicketService(db).get_all_tickets(
            event_id=event_id,
            organizer_id=organizer_id,
            page=page,
            per_page=per_page,
        )

    @router.get(
        "/organizer/tickets/", dependencies=[rate_limit], response_model=list[TicketOut]
    )
    @safe_handler
    async def get_organizer_tickets(
        self,
        page: int = 1,
        per_page: int = 20,
        current_user: User = Depends(require_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        return await TicketService(db).get_organizer_tickets(
            organizer_id=current_user.id,
            page=page,
            per_page=per_page,
        )
