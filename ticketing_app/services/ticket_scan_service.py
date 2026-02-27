from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from models.enums import TicketStatus
from repositories.ticket_repo import TicketRepo


class TicketScanService:

    def __init__(self, db):
        self.db = db

        self.ticket_repo = TicketRepo(db)

    async def scan_ticket_with_qr_code(self, qr_code: str, current_user):

        async with self.db.begin():

            ticket = await self.ticket_repo.get_for_scan_with_qrcode(qr_code)

            if not ticket:
                raise HTTPException(404, "Invalid Ticket")

            if ticket.status == TicketStatus.CHECKED_IN:
                raise HTTPException(
                    400,
                    detail={
                        "message": "Ticket already used",
                        "checked_in_at": ticket.checked_in_at.isoformat()
                        if ticket.checked_in_at else None,
                        "checked_in_by": ticket.checked_in_by if ticket.checked_in_by else None

                    }
                )

            if ticket.status not in{
                TicketStatus.SOLD
            }:
                raise HTTPException(
                    400,
                    f"Ticket is not valid for entry. Status: {ticket.status.value}"
                )

            if ticket.status == TicketStatus.SOLD:
                ticket.status = TicketStatus.CHECKED_IN
                ticket.updated_at = datetime.utcnow()
                ticket.checked_in_at = datetime.utcnow()
                ticket.checked_in_by = current_user.id

                await self.db.flush()

        return {
            "success": True,
            "message": "Entry Granted",
            "ticket_number": ticket.ticket_number,
            "status": ticket.status.value,
            "event": ticket.event.title,
            "event_date": ticket.event.start_time.isoformat(),
            "name": f"{ticket.user.first_name} {ticket.user.last_name}",
            "ticket_type": ticket.ticket_type.ticket_type.value,
            "venue": ticket.event.venue.name if ticket.event.venue else None,
        }

    async def scan_ticket_with_ticket_number(self, ticket_number: str, current_user):

        async with self.db.begin():  

            ticket = await self.ticket_repo.get_for_scan_with_ticket_number(ticket_number)

            if not ticket:
                raise HTTPException(404, "Invalid Ticket")

            if ticket.status == TicketStatus.CHECKED_IN:
                raise HTTPException(
                    400,
                    detail={
                        "message": "Ticket already used",
                        "checked_in_at": ticket.checked_in_at.isoformat()
                        if ticket.checked_in_at else None,
                        "checked_in_by": ticket.checked_in_by if ticket.checked_in_by else None
                    }
                )

            if ticket.status not in{
                TicketStatus.SOLD
            }:
                raise HTTPException(
                    400,
                    f"Ticket is not valid for entry. Status: {ticket.status.value}"
                )

            if ticket.status == TicketStatus.SOLD:
                ticket.status = TicketStatus.CHECKED_IN
                ticket.updated_at = datetime.utcnow()
                ticket.checked_in_at = datetime.utcnow()
                ticket.checked_in_by = current_user.id

                await self.db.flush()

        return {
            "success": True,
            "message": "Entry Granted",
            "ticket_number": ticket.ticket_number,
            "status": ticket.status.value,
            "event": ticket.event.title,
            "event_date": ticket.event.start_time.isoformat(),
            "name": f"{ticket.user.first_name} {ticket.user.last_name}",
            "ticket_type": ticket.ticket_type.ticket_type.value,
            "venue": ticket.event.venue.name if ticket.event.venue else None,
        }

    async def verify_ticket(self, ticket_number: str):

        ticket = await self.ticket_repo.verify_ticket(ticket_number)
        if not ticket:
                raise HTTPException(404, "Invalid Ticket")

        return {
            "ticket_number": ticket.ticket_number,
            "status": ticket.status.value,
            "event": ticket.event.title,
            "name": f"{ticket.user.first_name} {ticket.user.last_name}",
            "ticket_type": ticket.ticket_type.ticket_type.value,
            "venue": ticket.event.venue.name if ticket.event.venue else None,
        }
