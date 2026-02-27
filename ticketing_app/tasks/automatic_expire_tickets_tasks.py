from datetime import datetime, timedelta
from celery import shared_task
from core.get_db import SyncSessionLocal
from models.models import Ticket, EventTicketType
from models.enums import TicketStatus
from sqlalchemy import update, select
import httpx

@shared_task(name="automatic_expire_reserved_tickets_batch",autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},)
def auto_expire_reserved_tickets_batch():

    db = SyncSessionLocal()

    try:
        twelve_hours_ago = datetime.utcnow() - timedelta(hours=12)

        # 1️⃣ Get all expired reserved tickets
        expired_tickets = db.execute(
            select(Ticket)
            .where(
                Ticket.status == TicketStatus.RESERVED,
                Ticket.created_at < twelve_hours_ago,
            )
        ).scalars().all()

        if not expired_tickets:
            db.close()
            return "No expired tickets"

        # 2️⃣ Restore inventory + cancel ticket
        for ticket in expired_tickets:

            # Restore sold_quantity
            db.execute(
                update(EventTicketType)
                .where(EventTicketType.id == ticket.ticket_type_id)
                .values(
                    sold_quantity=EventTicketType.sold_quantity - ticket.quantity
                )
            )

            # Cancel ticket
            ticket.status = TicketStatus.CANCELLED

        db.commit()
        return f"Expired {len(expired_tickets)} tickets"

    except Exception as e:
        db.rollback()
        print(f"[Expire Batch Error] {e}")
        raise

    finally:
        db.close()