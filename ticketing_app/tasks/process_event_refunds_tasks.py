
import httpx
from celery import shared_task
from core.get_db import SyncSessionLocal
from models.enums import PaymentStatus
from models.models import Payment

from .refund_single_payments_process_tasks import refund_single_payment


@shared_task(name="process_event_refunds",  autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
             retry_backoff=True,
             retry_kwargs={"max_retries": 3},)
def process_event_refunds(event_str: str):

    db = SyncSessionLocal()

    try:
        event_id = int(event_str)
        payment_ids = (
            db.query(Payment.id)
            .filter(
                Payment.event_id == event_id,
                Payment.status == PaymentStatus.COMPLETED
            )
            .all()
        )

        for (payment_id,) in payment_ids:
            refund_single_payment.delay(payment_id)

    finally:
        db.close()
