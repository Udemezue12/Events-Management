import httpx
from celery import shared_task
from core.get_db import SyncSessionLocal
from services.generate_multipe_tickets import GenerateMultipleTicketService


@shared_task(
    name="generate_ticket_pass",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_ticket_pass_tasks(ticket_id_str: str):
    try:
        ticket_id = int(ticket_id_str)

        if not ticket_id:
            raise ValueError("Invalid Ticket ID")

        updated = generate(
            ticket_id=ticket_id
        )

        return updated

    except Exception:
        raise


def generate(ticket_id: int):
    db = SyncSessionLocal()

    try:
        return GenerateMultipleTicketService(db).generate_ticket_pass(
            ticket_id=ticket_id
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
