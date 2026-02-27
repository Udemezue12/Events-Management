from repositories.event_ticket_repo import EventTicketRepo

from repositories.event_repo import EventRepo
from fastapi import HTTPException


class EventTicketService:
    def __init__(self, db):
        self.repo = EventTicketRepo(db)
        self.event_repo = EventRepo(db)

    async def create(
        self, payload, current_user, event_id
    ):
        event = await self.event_repo.get_event_by_id(event_id)
        if not event or not event.is_active:
            raise HTTPException(400, "Event has been cancelled or not found")
        if event.created_by != current_user.id:
            raise HTTPException(400, "You did not create this event")
        ticket = await self.repo.create_event_ticket(
            event_id=event_id, ticket_type=payload.ticket_type, total_quantity=payload.total_quantity, price=payload.price
        )
        return {
            "id": ticket.id,
            "event_id": ticket.event_id,
            "total_quantity": ticket.total_quantity,
            "price": ticket.price,
            "ticket_type": ticket.ticket_type
        }
