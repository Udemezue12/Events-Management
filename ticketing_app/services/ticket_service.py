from asyncio import create_task as asyncio_task
from asyncio import run as asyncio_run
from datetime import datetime
from typing import List

from core.cache import cache
from core.threads import run_in_thread
from core.utils import publish_event
from repositories.ticket_repo import TicketRepo
from worker.celery_tasks import expire_old_tickets


class TicketService:
    def __init__(self, db):
        self.repo:TicketRepo = TicketRepo(db)

    async def reserve_ticket(self, user_id: int, event_id: int):
       
        try:
            event = await self.repo.get_event_by_id(event_id)
            if not event:
                raise ValueError("Event not found")
            if event.tickets_sold >= event.total_tickets:
                raise ValueError("Event sold out")

            ticket = await self.repo.create_ticket(user_id, event_id)
            await self.repo.increment_tickets_sold(event)

            expire_old_tickets.apply_async((ticket.id,), countdown=120)

            await run_in_thread(
                asyncio_run,
                publish_event(
                    "ticket.reserved",
                    {
                        "ticket_id": ticket.id,
                        "user_id": user_id,
                        "event_id": event_id,
                        "reserved_at": datetime.utcnow().isoformat(),
                    },
                ),
            )

            try:
                asyncio_task(cache.set_json("events:stale", {"stale": True}))
                asyncio_task(cache.delete("events:list"))
            except Exception as cache_error:
                print(f"[Cache warning] Could not update event cache: {cache_error}")

            return ticket
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

        await run_in_thread(
            asyncio_run,
            publish_event(
                "ticket.paid",
                {
                    "ticket_id": ticket_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            ),
        )

        await cache.set_json(f"ticket:{ticket_id}", {"status": "paid"})
        await cache.delete("events:list")

        return {
            "message": "Ticket marked as paid successfully",
            "ticket_id": ticket_id,
            "status": "paid",
        }

    async def get_user_ticket_history(self, user_id) -> List[dict]:
        cache_key = f"user:{user_id}:ticket_history"
        try:
            cached = await cache.get_json(cache_key)
            if cached:
                return cached
            tickets = await self.repo.get_tickets_by_user(user_id)
            if not tickets:
                return []
            await cache.set_json(cache_key, tickets, ttl=300)

            await run_in_thread(
                asyncio_run,
                publish_event(
                    "user.tickets",
                    {
                        "user_id": user_id,
                        "tickets": tickets,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                ),
            )
            return tickets
        except Exception as e:
            print(f"Error fetching ticket history: {e}")
            raise e
