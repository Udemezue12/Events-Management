import logging
from typing import List
from core.breaker import breaker
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from fastapi import APIRouter, Depends, HTTPException
from fastapi_utils.cbv import cbv
from repositories.ticket_repo import TicketRepo
from schemas.schema import TicketCreate, TicketOut, TicketHistoryResponse
from services.ticket_service import TicketService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Tickets"])


@cbv(router)
class TicketsRoutes:
    @router.post(
        "/tickets/reserve", dependencies=[rate_limit], response_model=TicketOut
    )
    @safe_handler
    async def reserve_ticket(
        self, data: TicketCreate, db: AsyncSession = Depends(get_db_async)
    ):
        async def handler():
            ticket = await TicketService(db).reserve_ticket(
                user_id=data.user_id, event_id=data.event_id
            )
            return ticket

        return await breaker.call(handler)

    @router.post("/{ticket_id}/pay", dependencies=[rate_limit])
    @safe_handler
    async def pay_ticket(
        self, ticket_id: int, db: AsyncSession = Depends(get_db_async)
    ):
        async def handler():
            result = await TicketService(db).mark_as_paid(ticket_id)
            return {"message": "Ticket Paid successfully", **result}

        return await breaker.call(handler)

    @router.get(
        "/users/{user_id}/history/tickets",
        dependencies=[rate_limit],
        response_model=List[TicketHistoryResponse],
    )
    @safe_handler
    async def get_user_tickets(
        self, user_id: int, db: AsyncSession = Depends(get_db_async)
    ):
        async def handler():
            tickets = await TicketService(db).get_user_ticket_history(user_id)
            if not tickets:
                raise HTTPException(status_code=404, detail="No ticket history found")
            return tickets

        return await breaker.call(handler)
