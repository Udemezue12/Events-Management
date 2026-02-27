

from typing import Optional

from models.enums import PaymentStatus, PaymentMethod
from models.models import Event, Payment, Ticket, PaymentItem
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload


class PaymentRepo:
    def __init__(self, db):
        self.db = db

    async def create_payment(
        self,
        user_id: int,
        event_id: int,
        quantity: int,
        method: PaymentMethod,
        status: PaymentStatus,
    )->Payment:

        payment = Payment(
            user_id=user_id,
            event_id=event_id,
            payment_method=method,
            ticket_quantity=quantity,
            status=status,
        )

        self.db.add(payment)

        try:
            await self.db.flush()

        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def create_payment_item(self, payment_id: int, ticket_type_id: int, quantity: int, unit_price: float, total_price: float):
        try:
            payment_item = PaymentItem(
                payment_id=payment_id,
                ticket_type_id=ticket_type_id,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
            )

            self.db.add(payment_item)

        except SQLAlchemyError:
            await self.db.rollback()
            raise

    def sync_db_commit(self):
        try:
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            raise
    async def db_commit(self):
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def set_reference(self, payment_id: int, reference: str):
        stmt = (
            update(Payment).where(Payment.id ==
                                  payment_id).values(reference=reference)
        )
        try:
            await self.db.execute(stmt)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    def sync_set_reference(self, payment_id: int, reference: str):
        stmt = (
            update(Payment).where(Payment.id ==
                                  payment_id).values(reference=reference)
        )
        try:
            self.db.execute(stmt)
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            raise

    async def get_payment_by_id(self, payment_id: int) -> Optional[Payment]:
        result = await self.db.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

    async def get_by_reference(self, reference: str) -> Optional[Payment]:
        result = await self.db.execute(
            select(Payment).where(Payment.reference == reference).options(
                selectinload(Payment.ticket)
                .selectinload(Ticket.event)
                .joinedload(Event.venue),
                selectinload(Payment.ticket).joinedload(Ticket.ticket_types)
                .selectinload(Ticket.event)
                .joinedload(Event.creator),
                selectinload(Payment.event).joinedload(Event.venue),
                selectinload(Payment.event).joinedload(Event.creator),
                selectinload(Payment.user),
            )
        )
        return result.scalar_one_or_none()

    def sync_get_reference(self, reference: str) -> Optional[Payment]:
        result = self.db.execute(
            select(Payment).where(Payment.reference == reference).options(
                selectinload(Payment.ticket)
                .selectinload(Ticket.event)
                .joinedload(Event.venue),
                selectinload(Payment.ticket).joinedload(Ticket.ticket_types)
                .selectinload(Ticket.event)
                .joinedload(Event.creator),
                selectinload(Payment.event).joinedload(Event.venue),
                selectinload(Payment.event).joinedload(Event.creator),
                selectinload(Payment.user),
            )
        )
        return result.scalar_one_or_none()

    async def update_status(self, payment_id: int, status: PaymentStatus):
        stmt = update(Payment).where(
            Payment.id == payment_id).values(status=status)
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
            .order_by(Payment.created_at.desc())
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

    def sync_update_status(
        self,
        payment_id: int,
        status: PaymentStatus,
    ):
        stmt = (
            update(Payment)
            .where(Payment.id == payment_id)
            .values(status=status)
        )
        try:
            self.db.execute(stmt)
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            raise

    async def set_transaction_id(self, payment_id: int, transaction_id: str):
        stmt = (
            update(Payment)
            .where(Payment.id == payment_id)
            .values(transaction_id=transaction_id)
        )
        try:
            await self.db.execute(stmt)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    def sync_set_transaction_id(self, payment_id: int, transaction_id: str):
        stmt = (
            update(Payment)
            .where(Payment.id == payment_id)
            .values(transaction_id=transaction_id)
        )
        try:
            self.db.execute(stmt)
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            raise
