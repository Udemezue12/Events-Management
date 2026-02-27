from datetime import datetime, timedelta

import httpx
from celery import shared_task
from core.get_db import SyncSessionLocal
from models.models import Ticket
from sqlalchemy import update
from repositories.ticket_repo import TicketRepo
from utils.sms_service import send_sms
from utils.sms_service import send_sms
from repositories.event_ticket_repo import EventTicketRepo
from utils.email_service import sync_send_event_email


@shared_task(
    name="sync_expire_reserved_tickets",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def expire_reserved_tickets_tasks(ticket_id: int):

    db = SyncSessionLocal()

    try:
        repo = TicketRepo(db)
        event_repo = EventTicketRepo(db)

        ticket = repo.sync_get_reserved_tickets(ticket_id)
        if not ticket:
            return
        
        user = ticket.user
        name = f"{user.last_name} {user.first_name}"
        sms_type = "ticket_expired"

        event_repo.sync_check_decrement(
            ticket.ticket_type_id, ticket.total_ticket_quantity)

        db.commit()

        if user:
            send_sms.sync_send_event_sms(
                phone_number=ticket.user.phone_number,
                sms_type=sms_type,
                name=name,
                event_title=ticket.event.title,
                ticket_id=ticket.id

            )
            sync_send_event_email(
                email=user.email,
                email_type=sms_type,
                name=name,
                event_name=ticket.event.title,
                ticket_id=ticket.id

            )

    except Exception as e:
        db.rollback()
        print(f"[Celery Task Error] expire_reserved_tickets: {e}")
        raise

    finally:
        db.close()
