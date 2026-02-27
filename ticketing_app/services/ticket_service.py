
from datetime import datetime
from typing import List

from core.cache import cache
from core.paginate import PaginatePage
from core.utils import publish_event
from fastapi import BackgroundTasks, HTTPException
from repositories.event_repo import EventRepo
from repositories.event_ticket_repo import EventTicketRepo
from repositories.ticket_repo import TicketRepo
from tasks.expire_tickets_tasks import expire_reserved_tickets_tasks
from utils.email_service import sync_send_event_email
from utils.sms_service import send_sms


class TicketService:
    def __init__(self, db):
        self.db = db
        self.repo: TicketRepo = TicketRepo(db)
        self.paginate: PaginatePage = PaginatePage()
        self.event_ticket_repo: EventTicketRepo = EventTicketRepo(db)
        self.event_repo: EventRepo = EventRepo(db)

    async def reserve_ticket(self, background_tasks: BackgroundTasks, user_id: int, event_id: int, items: list):

        try:
            async with self.db.begin():
                total_amount = 0
                total_quantity = 0
                response_items = []
                all_reserved_tickets = []
                event = await self.event_repo.get_by_id(event_id)
                if not event.is_active:
                    raise HTTPException(
                        400, "Event has been cancelled or is not active")
                for item in items:
                    ticket_type = await self.event_ticket_repo.get_by_id(item["ticket_type_id"], event_id)
                    if not ticket_type:
                        raise HTTPException(404, "Ticket type not found")
                    quantity = item["quantity"]

                    if ticket_type.available_quantity < quantity:
                        raise HTTPException(
                            400, "Not enough tickets available")
                    ticket_type.total_reserved_quantity += quantity
                    ticket_type.available_quantity -= quantity
                    unit_price = ticket_type.price
                    total_price = unit_price * quantity
                    total_amount += total_price
                    total_quantity += quantity

                    for _ in range(quantity):

                        ticket = await self.repo.create_ticket(
                            user_id=user_id, event_id=event_id, ticket_type_id=ticket_type.id,
                            price_paid=ticket_type.price
                        )
                        all_reserved_tickets.append(ticket)
                    response_items.append({
                        "ticket_type_id": ticket_type.id,
                        "ticket_type_name": ticket_type.ticket_type,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "total_price": total_price,
                    })

                await self.repo.sync_db_flush()
            for ticket in all_reserved_tickets:
                expire_reserved_tickets_tasks.apply_async(
                    args=[str(ticket.id)], countdown=60 * 60 * 12)

            user = all_reserved_tickets[0].user
            first_ticket = all_reserved_tickets[0]

            name = f"{user.last_name} {user.first_name}"

            sms_type = "ticket_reserved"

            if user.phone_number:
                background_tasks.add_task(
                    send_sms.sync_send_event_sms, user.phone_number, sms_type, name, event.title
                )
            if user.email:

                background_tasks.add_task(
                    sync_send_event_email, user.email, sms_type, name, event_name=event.title
                )

            await publish_event(
                "ticket.reserved",
                {
                    "ticket_id": first_ticket.id,
                    "user_id": user_id,
                    "event_id": event_id,
                    "reserved_at": datetime.utcnow().isoformat(),
                },
            ),

            await cache.async_set_json("events:stale", {"stale": True})
            await cache.delete_cache_keys_async("events:list", f"user:{user_id}:ticket_history")

            return {
                "message": "Tickets reserved successfully",
                "event_id": event_id,
                "items": response_items,
                "total_quantity": total_quantity,
                "total_amount": total_amount,
            }
        except Exception as e:
            print(f"Error reserving ticket: {e}")
            raise e

    async def mark_as_paid(self, ticket_id: int):

        ticket = await self.repo.get_ticket_by_id(ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
        if ticket.status == "paid":
            raise ValueError("Ticket already paid for")

        await self.repo.mark_ticket_as_paid(ticket_id)

        publish_event(
            "ticket.paid",
            {
                "ticket_id": ticket_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        ),

        # await cache.async_set_json(f"ticket:{ticket_id}", {"status": "paid"})
        await cache.async_delete("events:list")

        return {
            "message": "Ticket marked as paid successfully",
            "ticket_id": ticket_id,
            "status": "paid",
        }

    async def get_user_ticket(
        self, user_id, page: int = 1, per_page: int = 20
    ) -> List[dict]:
        cache_key = f"user:{user_id}:ticket_history:p{page}"
        try:
            cached = await cache.async_get_json(cache_key)
            if cached:
                return cached
            tickets = await self.repo.get_tickets_by_user(user_id)
            if not tickets:
                return []
            paginated_tickets = self.paginate.paginate(tickets, page, per_page)
            await cache.async_set_json(cache_key, paginated_tickets, ttl=300)

            await publish_event(
                "user.tickets",
                {
                    "user_id": user_id,
                    "tickets": tickets,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            ),

            return paginated_tickets
        except Exception as e:
            print(f"Error fetching ticket history: {e}")
            raise e

    async def get_all_tickets(
        self,
        event_id: int | None = None,
        organizer_id: int | None = None,
        page=1,
        per_page=20,
    ):
        cache_key = f"tickets:all:e{event_id}:o{organizer_id}:p{page}"
        cached = await cache.async_get_json(cache_key)
        if cached:
            return cached
        tickets = await self.repo.get_all_tickets(
            event_id=event_id, organizer_id=organizer_id
        )
        if not tickets:
            return []
        paginated_tickets = self.paginate.paginate(tickets, page, per_page)
        await cache.async_set_json(cache_key, paginated_tickets, ttl=300)
        return paginated_tickets

    async def get_organizer_tickets(self, organizer_id, page=1, per_page=20):
        cache_key = f"tickets:org:{organizer_id}:p{page}"

        cached = await cache.async_get_json(cache_key)
        if cached:
            return cached

        tickets = await self.repo.get_tickets_for_organizer(organizer_id=organizer_id, per_page=per_page, page=page)
        if not tickets:
            return []
        paginated_tickets = self.paginate.paginate(tickets, page, per_page)

        await cache.async_set_json(cache_key, paginated_tickets, ttl=300)
        return paginated_tickets
