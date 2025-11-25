from asyncio import create_task as asyncio_task
from datetime import datetime
from typing import List

from core.breaker import breaker
from core.paginate import PaginatePage
from core.cache import cache
from core.utils import publish_event
from repositories.ticket_repo import TicketRepo
from tasks.celery_tasks import tasks_app


class TicketService:
    def __init__(self, db):
        self.repo: TicketRepo = TicketRepo(db)
        self.paginate: PaginatePage = PaginatePage()

    async def reserve_ticket(self, user_id: int, event_id: int, quantity: int = 1):
        async def handler():
            try:
                event = await self.repo.get_event_by_id(event_id)
                if not event:
                    raise ValueError("Event not found")
                if event.tickets_sold + quantity > event.total_tickets:
                    raise ValueError("Not enough tickets available")

                ticket = await self.repo.create_ticket(
                    user_id, event_id, quantity=quantity
                )
                await self.repo.increment_tickets_sold(event, quantity)

                tasks_app.expire_tickets_task.apply_async((ticket.id,), countdown=120)

                await asyncio_task(
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
                    await cache.delete(f"user:{user_id}:ticket_history")

                except Exception as cache_error:
                    print(
                        f"[Cache warning] Could not update event cache: {cache_error}"
                    )

                return  ticket.as_dict()
            except Exception as e:
                print(f"Error reserving ticket: {e}")
                raise e

        return await breaker.call(handler)

    async def mark_as_paid(self, ticket_id: int):
        async def handler():
            ticket = await self.repo.get_ticket_by_id(ticket_id)
            if not ticket:
                raise ValueError("Ticket not found")
            if ticket.status == "paid":
                raise ValueError("Ticket already paid for")

            await self.repo.mark_ticket_as_paid(ticket_id)

            await asyncio_task(
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

        return await breaker.call(handler)

    async def get_user_ticket(
        self, user_id, page: int = 1, per_page: int = 20
    ) -> List[dict]:
        cache_key = f"user:{user_id}:ticket_history:p{page}"
        try:
            cached = await cache.get_json(cache_key)
            if cached:
                return cached
            tickets = await self.repo.get_tickets_by_user(user_id)
            if not tickets:
                return []
            paginated_tickets = self.paginate.paginate(tickets, page, per_page)
            await cache.set_json(cache_key, paginated_tickets, ttl=300)

            await asyncio_task(
                publish_event(
                    "user.tickets",
                    {
                        "user_id": user_id,
                        "tickets": tickets,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                ),
            )
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
        cached = await cache.get_json(cache_key)
        if cached:
            return cached
        tickets = await self.repo.get_all_tickets(
            event_id=event_id, organizer_id=organizer_id
        )
        if not tickets:
            return []
        paginated_tickets = self.paginate.paginate(tickets, page, per_page)
        await cache.set_json(cache_key, paginated_tickets, ttl=300)
        return paginated_tickets

    async def get_organizer_tickets(self, organizer_id, page=1, per_page=20):
        cache_key = f"tickets:org:{organizer_id}:p{page}"

        cached = await cache.get_json(cache_key)
        if cached:
            return cached

        tickets = await self.repo.get_tickets_for_organizer(organizer_id)
        if not tickets:
            return []
        paginated_tickets = self.paginate.paginate(tickets, page, per_page)

        await cache.set_json(cache_key, paginated_tickets, ttl=300)
        return paginated_tickets
