from models.models import Event, Ticket, EventTicketType

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from models.enums import TicketStatus, PDFStatus
from datetime import datetime, timezone, timedelta
from typing import Optional
from repositories.event_ticket_repo import EventTicketRepo
from sqlalchemy.orm import selectinload, joinedload


class TicketRepo:
    def __init__(self, db):
        self.db = db
        self.event_ticket_repo: EventTicketRepo = EventTicketRepo(db)
    async def update_check_in_status(self, ticket: Ticket, status):
        ticket.status = status
        await self.db.flush()
    async def update_status(self, ticket_id: int, payment_id: int, status: TicketStatus = TicketStatus.SOLD):
        stmt = update(Ticket).where(
            Ticket.id == ticket_id, Ticket.payment_id == payment_id).values(status=status)
        try:
            await self.db.execute(stmt)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def create_ticket(
        self, user_id: int, event_id: int,  ticket_type_id: int, price_paid: float,
    ):

        try:
            # updated_row = await self.event_ticket_repo.check_sold(ticket_type_id=ticket_type_id, quantity=quantity)
            # if not updated_row:
            #     raise ValueError("Insufficient ticket inventory")

            # price = updated_row.price
            # total_price = price * quantity
            ticket = Ticket(
                user_id=user_id,
                event_id=event_id,
                ticket_type_id=ticket_type_id,
                # quantity=quantity,
                price_paid=price_paid,
                status=TicketStatus.RESERVED,
            )
            self.db.add(ticket)

        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def finalize_ticket_sale(self, ticket: Ticket):
        async with self.db.begin():

            # Update ticket status
            ticket.status = TicketStatus.SOLD
            self.db.add(ticket)

            # Update ticket type revenue
            stmt = (
                update(EventTicketType)
                .where(EventTicketType.id == ticket.ticket_type_id)
                .values(
                    total_price_gotten=EventTicketType.total_price_gotten + ticket.price_paid
                )
            )

            await self.db.execute(stmt)

    async def increment_tickets_sold(self, event: Event, quantity: int = 1):
        event.tickets_sold += quantity
        self.db.add(event)
        try:
            await self.db.commit()
            await self.db.refresh(event)
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    def sync_increment_tickets_sold(self, event: Event, quantity: int = 1):
        event.tickets_sold += quantity
        self.db.add(event)
        try:
            self.db.commit()
            self.db.refresh(event)
        except SQLAlchemyError:
            self.db.rollback()
            raise

    async def increment_event_type_tickets_sold(self, event_type: EventTicketType, quantity: int = 1):
        event_type.sold_quantity += quantity
        self.db.add(event_type)
        try:
            await self.db.commit()
            await self.db.refresh(event_type)
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_ticket_id(self, ticket_id: int) -> Optional[Ticket]:
        ticket = await self.db.execute(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
        return ticket.scalar_one_or_none()

    def sync_get_ticket_id(self, ticket_id: int) -> Optional[Ticket]:
        ticket = self.db.execute(select(Ticket).where(
            Ticket.id == ticket_id).options(
            selectinload(Ticket.user),
            selectinload(Ticket.event).selectinload(Event.venue),
            selectinload(Ticket.ticket_type),
            selectinload(Ticket.payment)
        ).with_for_update())
        return ticket.scalar_one_or_none()

    async def mark_ticket_as_paid(self, ticket_id: int, payment_id: int) -> Ticket:
        async with self.db.begin():
            stmt = (
                update(Ticket)
                .where(
                    Ticket.id == ticket_id,
                    Ticket.status == TicketStatus.RESERVED
                )
                .values(
                    status=TicketStatus.SOLD, payment_id=payment_id
                )
                .returning(Ticket)
            )

            result = await self.db.execute(stmt)
            ticket = result.scalar_one_or_none()

            if not ticket:
                raise ValueError(
                    "Ticket not found or not in RESERVED state"
                )

        return ticket

    def sync_mark_ticket_as_paid(self, ticket_id: int) -> Ticket:
        ticket = self.sync_get_ticket_id(ticket_id)

        if ticket:
            ticket.status = TicketStatus.CONFIRMED
            self.db.add(ticket)
            try:
                self.db.commit()
                self.db.refresh(ticket)
            except SQLAlchemyError:
                self.db.rollback()
                raise
        return ticket

    # async def marks_ticket_as_paid(self, ticket_id: int):
    #   await self.db.execute(update(Ticket).where(Ticket.#id == ticket_id).values(status="paid"))
    #   await self.db.commit()

    async def get_ticket_by_id(self, ticket_id: int) -> Ticket | None:
        result = await self.db.execute(
            select(Ticket)
            .options(selectinload(Ticket.event), selectinload(Ticket.ticket_type))
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
            self, event_id: int | None = None, organizer_id: int | None = None, page: int = 1, per_page=20):
        offset = (page - 1) * per_page
        stmt = (
            select(Ticket)
            .join(Ticket.user)
            .join(Ticket.event)
            .options(
                selectinload(Ticket.user),
                selectinload(Ticket.event).selectinload(Event.venue),
            ).order_by(Ticket.created_at.desc())
            .limit(per_page)
            .offset(offset)
        )

        if event_id:
            stmt = stmt.where(Ticket.event_id == event_id)

        if organizer_id:
            stmt = stmt.where(Event.created_by == organizer_id)

        result = await self.db.execute(stmt)
        return [t.as_dict() for t in result.scalars().all()]

    async def get_tickets_for_organizer(self, organizer_id: int, page: int = 1, per_page=20):
        offset = (page - 1) * per_page
        stmt = (
            select(Ticket)
            .join(Ticket.user)
            .join(Ticket.event)
            .where(Event.created_by == organizer_id)
            .options(
                selectinload(Ticket.user),
                selectinload(Ticket.event).selectinload(Event.venue),
            ).order_by(Ticket.created_at.desc())
            .limit(per_page)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        return [t.as_dict() for t in result.scalars().all()]

    def sync_get_reserved_tickets(self, ticket_id: int) -> Optional[Ticket]:
        two_min_ago = datetime.utcnow() - timedelta(hours=12)

        try:
            stmt = (
                select(Ticket)
                .where(Ticket.status == TicketStatus.RESERVED, Ticket.created_at < two_min_ago, Ticket.id == ticket_id).options(
                    selectinload(Ticket.ticket_type),
                    selectinload(Ticket.user),
                    selectinload(Ticket.event).joinedload(Event.venue),
                    selectinload(Ticket.payment)


                ).with_for_update()
            )

            result = self.db.execute(stmt)

            ticket = result.scalar_one_or_none()
            if not ticket:
                return None
            ticket.status = TicketStatus.CANCELLED
            self.db.commit()
            return ticket

        except SQLAlchemyError:
            self.db.rollback()
            raise

    def sync_set_ticket_url(self, ticket_id: int, ticket_pass_url: str, ticket_pass_public_id: str):
        stmt = (
            update(Ticket)
            .where(Ticket.id == ticket_id)
            .values(ticket_pass_url=ticket_pass_url, ticket_pass_public_id=ticket_pass_public_id)
        )
        try:
            self.db.execute(stmt)
            self.db.commit()

        except SQLAlchemyError:
            self.db.rollback()
            raise

    def sync_update_pdf_status(self, ticket_id: int, status: PDFStatus):
        stmt = (
            update(Ticket)
            .where(Ticket.id == ticket_id)
            .values(pdf_status=status)
        )
        try:
            self.db.execute(stmt)
            self.db.commit()

        except SQLAlchemyError:
            self.db.rollback()
            raise

    async def get_reserved_tickets_for_update(
        self,
        user_id: int,
        event_id: int,
        quantity: int
    ) -> list[Ticket]:
        stmt = (
            select(Ticket)
            .where(
                Ticket.user_id == user_id,
                Ticket.event_id == event_id,
                Ticket.status == TicketStatus.RESERVED
            )
            .limit(quantity)
            .with_for_update()
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()
    def sync_get_reserved_tickets_for_update(
        self,
        user_id: int,
        event_id: int,
        quantity: int
    ) -> list[Ticket]:
        stmt = (
            select(Ticket)
            .where(
                Ticket.user_id == user_id,
                Ticket.event_id == event_id,
                Ticket.status == TicketStatus.RESERVED
            )
            .limit(quantity)
            .with_for_update()
        )

        result = self.db.execute(stmt)
        return result.scalars().all()

    async def get_user_reserved_tickets(
        self,
        user_id: int,
        event_id: int,
    ) -> list[Ticket]:
        stmt = (
            select(Ticket)
            .where(
                Ticket.user_id == user_id,
                Ticket.event_id == event_id,
                Ticket.status == TicketStatus.RESERVED
            )

            .with_for_update()
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()

    def sync_set_ticket_details(self, ticket_id: int, ticket_number: str, barcode: str):
        stmt = (
            update(Ticket)
            .where(Ticket.id == ticket_id)
            .values(ticket_number=ticket_number, barcode=barcode)
        )
        try:
            self.db.execute(stmt)
            self.db.commit()

        except SQLAlchemyError:
            self.db.rollback(

            )
            raise
    async def get_for_scan_with_ticket_number(self, ticket_number: str) -> Ticket | None:
        stmt = (
            select(Ticket)
            .where(Ticket.ticket_number == ticket_number)
            .options(
                selectinload(Ticket.user),
                selectinload(Ticket.event).joinedload(Event.venue),
                selectinload(Ticket.ticket_type),
            )
            .with_for_update()  
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    async def get_for_scan_with_qrcode(self, qr_code: str) -> Ticket | None:
        stmt = (
            select(Ticket)
            .where(Ticket.barcode == qr_code)
            .options(
                selectinload(Ticket.user),
                selectinload(Ticket.event).joinedload(Event.venue),
                selectinload(Ticket.ticket_type),
            )
            .with_for_update()  # 🔥 locks row
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    async def verify_ticket(self, ticket_number: str) -> Ticket | None:
        stmt = (
            select(Ticket)
            .where(Ticket.ticket_number == ticket_number)
            .options(
                selectinload(Ticket.user),
                selectinload(Ticket.event).joinedload(Event.venue),
                selectinload(Ticket.ticket_type),
            )
            .with_for_update()  # 🔥 locks row
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    

    def sync_db_commit(self):
        try:
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            raise

    def sync_db_flush(self):
        try:
            self.db.flush()
        except SQLAlchemyError:
            self.db.rollback()
            raise
    async def db_flush(self):
        try:
            self.db.flush()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    def sync_db_rollback(self):

        self.db.rollback()
