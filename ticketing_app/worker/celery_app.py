from celery import Celery
from celery.schedules import crontab
from core.settings import settings

celery_app = Celery(
    "events_tasks",
    broker=settings.CELERY_REDIS_URL,
    backend=settings.CELERY_REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        
        "expire-tickets": {
            "task": "automatic_expire_reserved_tickets_batch",
            "schedule": crontab(minute="*/10"),
        },
    },
)

from tasks import expire_tickets_tasks
from tasks import upload_venue_image_tasks
from tasks import upload_event_image_tasks
from tasks import automatic_expire_tickets_tasks
from tasks import refund_single_payments_process_tasks
from tasks import process_event_refunds_tasks
from tasks import retry_payment_tasks

app = celery_app