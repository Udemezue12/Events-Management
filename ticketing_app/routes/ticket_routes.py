import logging
from typing import List

from core.breaker import breaker
from core.get_current_user import get_current_user
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.validators import validate_csrf_dependency
from core.throttling import rate_limit
from fastapi import APIRouter, Depends, HTTPException
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
    @router.post("/reserve", dependencies=[rate_limit], response_model=TicketOut)
    @safe_handler
    async def reserve_ticket(
        self,
        data: TicketCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        async def handler():
            if current_user.role.name not in {"admin", "organizer", "attendee"}:
                raise HTTPException(status_code=403, detail="Not permitted")
            ticket = await TicketService(db).reserve_ticket(
                user_id=current_user.id,
                event_id=data.event_id,
                quantity=data.quantity,
            )
            return ticket

        return await breaker.call(handler)

    @router.post("/{ticket_id}/pay", dependencies=[rate_limit])
    @safe_handler
    async def mark_ticket_paid(
        self,
        ticket_id: int,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        async def handler():
            if current_user.role.name not in ["admin", "organizer"]:
                raise HTTPException(status_code=403, detail="Not permitted")
            result = await TicketService(db).mark_as_paid(ticket_id=ticket_id)
            return {"message": "Ticket Paid successfully", **result}

        return await breaker.call(handler)

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
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        async def handler():
            if current_user.role.name not in {"admin", "organizer", "attendee"}:
                raise HTTPException(status_code=403, detail="Not permitted")
            tickets = await TicketService(db).get_user_ticket(
                user_id=current_user.id, page=page, per_page=per_page
            )
            if not tickets:
                raise HTTPException(status_code=404, detail="No Ticket found")
            return tickets

        return await breaker.call(handler)

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
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        async def handler():
            if current_user.role.name != "admin":
                raise HTTPException(status_code=403, detail="Not permitted")
            tickets = await TicketService(db).get_all_tickets(
                event_id=event_id,
                organizer_id=organizer_id,
                page=page,
                per_page=per_page,
            )
            if not tickets:
                raise HTTPException(status_code=404, detail="No Tickets Found")
            return tickets

        return await breaker.call(handler)

    @router.get(
        "/organizer/tickets/", dependencies=[rate_limit], response_model=list[TicketOut]
    )
    @safe_handler
    async def get_organizer_tickets(
        self,
        page: int = 1,
        per_page: int = 20,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
        async def handler():
            if current_user.role.name not in ["admin", "organizer"]:
                raise HTTPException(status_code=403, detail="Not permitted")
            tickets = await TicketService(db).get_organizer_tickets(
                organizer_id=current_user.id,
                page=page,
                per_page=per_page,
            )
            if not tickets:
                raise HTTPException(status_code=404, detail="No Tickets Found")
            return tickets

        return await breaker.call(handler)
