from models.models import Event, Ticket
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError


class TicketRepo:
    def __init__(self, db):
        self.db = db

    async def get_event_by_id(self, event_id: int) -> Event:
        return await self.db.scalar(select(Event).where(Event.id == event_id))

    async def create_ticket(
        self, user_id: int, event_id: int, quantity: int = 1
    ) -> Ticket:
        ticket = Ticket(
            user_id=user_id, event_id=event_id, status="reserved", quantity=quantity
        )
        self.db.add(ticket)
        try:
            await self.db.commit()
            await self.db.refresh(ticket)
            return ticket
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def increment_tickets_sold(self, event: Event, quantity: int = 1):
        event.tickets_sold += quantity
        self.db.add(event)
        try:
            await self.db.commit()
            await self.db.refresh(event)
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def mark_ticket_as_paid(self, ticket_id: int) -> Ticket:
        ticket = await self.db.scalar(select(Ticket).where(Ticket.id == ticket_id))
        if ticket:
            ticket.status = "paid"
            self.db.add(ticket)
            try:
                await self.db.commit()
                await self.db.refresh(ticket)
            except SQLAlchemyError:
                await self.db.rollback()
                raise
        return ticket

    # async def marks_ticket_as_paid(self, ticket_id: int):
    #   await self.db.execute(update(Ticket).where(Ticket.#id == ticket_id).values(status="paid"))
    #   await self.db.commit()

    async def get_ticket_by_id(self, ticket_id: int) -> Ticket | None:
        result = await self.db.execute(
            select(Ticket)
            .options(selectinload(Ticket.event))
            .where(Ticket.id == ticket_id)
        )
        return result.scalars().first()

    async def get_tickets_by_user(self, user_id: int):
        stmt = (
            select(Ticket)
            .join(Ticket.user)
            .options(
                selectinload(Ticket.user),
                selectinload(Ticket.event).selectinload(Event.venue),
            )
            .where(Ticket.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return [t.as_dict() for t in result.scalars().all()]

    async def get_all_tickets(
        self, event_id: int | None = None, organizer_id: int | None = None
    ):
        stmt = (
            select(Ticket)
            .join(Ticket.user)
            .join(Ticket.event)
            .options(
                selectinload(Ticket.user),
                selectinload(Ticket.event).selectinload(Event.venue),
            )
        )

        if event_id:
            stmt = stmt.where(Ticket.event_id == event_id)

        if organizer_id:
            stmt = stmt.where(Event.created_by == organizer_id)

        result = await self.db.execute(stmt)
        return [t.as_dict() for t in result.scalars().all()]

    async def get_tickets_for_organizer(self, organizer_id: int):
        stmt = (
            select(Ticket)
            .join(Ticket.user)
            .join(Ticket.event)
            .where(Event.created_by == organizer_id)
            .options(
                selectinload(Ticket.user),
                selectinload(Ticket.event).selectinload(Event.venue),
            )
        )

        result = await self.db.execute(stmt)
        return [t.as_dict() for t in result.scalars().all()]
