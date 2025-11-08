from models.models import Event, Ticket
from sqlalchemy import select, text



class TicketRepo:
    def __init__(self, db):
        self.db = db

    async def get_event_by_id(self, event_id: int) -> Event:
        return await self.db.scalar(select(Event).where(Event.id == event_id))

    async def create_ticket(self, user_id: int, event_id: int) -> Ticket:
        ticket = Ticket(user_id=user_id, event_id=event_id, status="reserved")
        self.db.add(ticket)
        try:
            await self.db.commit()
            await self.db.refresh(ticket)
            return ticket
        except:
            await self.db.rollback()
            raise

    async def increment_tickets_sold(self, event: Event):
        event.tickets_sold += 1
        self.db.add(event)
        await self.db.commit()

    async def mark_ticket_as_paid(self, ticket_id: int) -> Ticket:
        ticket = await self.db.scalar(select(Ticket).where(Ticket.id == ticket_id))
        if ticket:
            ticket.status = "paid"
            self.db.add(ticket)
            await self.db.commit()
            await self.db.refresh(ticket)
        return ticket

    async def get_tickets_by_user(self, user_id: int):
        query = text("""
            SELECT 
                t.id, t.status, t.created_at AS reserved_at,
                e.title AS event_title, e.venue_address AS location
            FROM tickets t
            JOIN events e ON e.id = t.event_id
            WHERE t.user_id = :user_id
            ORDER BY t.created_at DESC
        """)
        result = await self.db.execute(query, {"user_id": user_id})
        return [dict(row) for row in result.mappings().all()]
    async def get_ticket_by_id(self, ticket_id: int) -> Ticket | None:
        return await self.db.scalar(select(Ticket).where(Ticket.id == ticket_id))
