from models.enums import PaymentStatus
from models.models import Event, Payment, Ticket
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload


class PaymentRepo:
    def __init__(self, db):
        self.db = db

    async def create_payment(
        self,
        user_id: int,
        ticket: Ticket,
        method: str,
        status: PaymentStatus,
    ):
        ticket_amount = ticket.event.ticket_price * ticket.quantity
        ticket.price_paid = ticket_amount
        payment = Payment(
            user_id=user_id,
            ticket_id=ticket.id,
            event_id=ticket.event_id,
            amount=ticket_amount,
            payment_method=method,
            ticket_quantity=ticket.quantity,
            status=status,
        )

        self.db.add(ticket)
        self.db.add(payment)

        try:
            await self.db.commit()
            await self.db.refresh(payment)
            await self.db.refresh(ticket)
            return payment
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def set_reference(self, payment_id: int, reference: str):
        stmt = (
            update(Payment).where(Payment.id == payment_id).values(reference=reference)
        )
        try:
            await self.db.execute(stmt)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_payment_by_id(self, payment_id: int):
        result = await self.db.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

    async def get_by_reference(self, reference: str):
        result = await self.db.execute(
            select(Payment).where(Payment.reference == reference)
        )
        return result.scalar_one_or_none()

    async def update_status(self, payment_id: int, status: PaymentStatus):
        stmt = update(Payment).where(Payment.id == payment_id).values(status=status)
        try:
            await self.db.execute(stmt)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_user_payments(self, user_id: int, offset: int = 0, limit: int = 50):
        stmt = (
            select(Payment)
            .options(
                selectinload(Payment.ticket)
                .selectinload(Ticket.event)
                .joinedload(Event.venue),
                selectinload(Payment.ticket)
                .selectinload(Ticket.event)
                .joinedload(Event.creator),
                selectinload(Payment.event).joinedload(Event.venue),
                selectinload(Payment.event).joinedload(Event.creator),
                selectinload(Payment.user),
            )
            .where(Payment.user_id == user_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        payments = result.scalars().all()
        return payments

    async def get_all_payments(self, offset: int = 0, limit: int = 50):
        stmt = (
            select(Payment)
            .options(
                selectinload(Payment.ticket)
                .selectinload(Ticket.event)
                .joinedload(Event.venue),
                selectinload(Payment.ticket)
                .selectinload(Ticket.event)
                .joinedload(Event.creator),
                selectinload(Payment.event).joinedload(Event.venue),
                selectinload(Payment.event).joinedload(Event.creator),
                selectinload(Payment.user),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_payments_for_organizer(
        self, organizer_id: int, offset: int = 0, limit: int = 50
    ):
        stmt = (
            select(Payment)
            .join(Payment.ticket)
            .join(Ticket.event)
            .options(
                selectinload(Payment.ticket)
                .selectinload(Ticket.event)
                .joinedload(Event.venue),
                selectinload(Payment.ticket)
                .selectinload(Ticket.event)
                .joinedload(Event.creator),
                selectinload(Payment.event).joinedload(Event.venue),
                selectinload(Payment.event).joinedload(Event.creator),
                selectinload(Payment.user),
            )
            .where(Event.created_by == organizer_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
