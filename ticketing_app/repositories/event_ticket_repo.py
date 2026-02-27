from models.models import Event, EventTicketType
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from models.enums import TicketType
from typing import Optional


class EventTicketRepo:
    def __init__(self, db):
        self.db = db

    async def create_event_ticket(
        self, event_id: int, ticket_type: TicketType, total_quantity: int, price: float
    ) -> EventTicketType:
        ticket = EventTicketType(
            event_id=event_id, ticket_type=ticket_type, total_quantity=total_quantity, price=price
        )
        self.db.add(ticket)
        try:
            await self.db.commit()
            await self.db.refresh(ticket)
            return ticket
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def check_sold(self, ticket_type_id: int, quantity: int):
        stmt = (
            update(EventTicketType)
            .where(
                EventTicketType.id == ticket_type_id,
                (EventTicketType.total_quantity -
                 EventTicketType.total_sold_quantity) >= quantity
            )
            .values(
                total_sold_quantity=EventTicketType.total_sold_quantity + quantity
            )
            .returning(
                EventTicketType
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_total_price_sold(self, ticket_type_id: int, price_paid: float):

        stmt = (
            update(EventTicketType)
            .where(EventTicketType.id == ticket_type_id)
            .values(
                total_price_sold=EventTicketType.total_price_sold + price_paid
            )
            .returning(EventTicketType)
        )

        result = await self.db.execute(stmt)
        ticket_type = result.scalar_one_or_none()

        if not ticket_type:
            raise ValueError("Ticket type not found")

        return ticket_type
    def sync_get_total_price_sold(self, ticket_type_id: int, price_paid: float):

        stmt = (
            update(EventTicketType)
            .where(EventTicketType.id == ticket_type_id)
            .values(
                total_price_sold=EventTicketType.total_price_sold + price_paid
            )
            .returning(EventTicketType)
        )

        result = self.db.execute(stmt)
        ticket_type = result.scalar_one_or_none()

        if not ticket_type:
            raise ValueError("Ticket type not found")

        return ticket_type

    def sync_check_decrement(self, ticket_type_id: int, quantity: int):
        try:
            self.db.execute(
                update(EventTicketType)
                .where(EventTicketType.id == ticket_type_id)
                .values(
                    total_reserved_quantity=EventTicketType.total_reserved_quantity - quantity
                )
            )
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            raise

    async def get_by_id(self, event_id: int, event_ticket_id: int) -> Optional[EventTicketType]:
        stmt = (
            select(EventTicketType)
            .where(EventTicketType.id == event_ticket_id, EventTicketType.event_id == event_id)
            .with_for_update()
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
