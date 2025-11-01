import asyncio
from datetime import datetime, timedelta

from .celery_app import celery_app, app
from .celery_events import publish_task_event
from core.get_db import AsyncSessionLocal
from models.models import Ticket
from sqlalchemy import update


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    try:
        sender.add_periodic_task(
            60.0, expire_old_tickets.s(), name="expire reserved tickets every 1 minute"
        )
    except Exception as e:
        print(f"Error setting up periodic tasks: {e}")
      
        pass


@celery_app.task(name="tasks.expire_tickets")
def expire_old_tickets():
    async def _expire():
        try:
            with AsyncSessionLocal() as db:
                two_min_ago = datetime.utcnow() - timedelta(minutes=2)
                await db.execute(
                    update(Ticket)
                    .where(Ticket.status == "reserved", Ticket.created_at < two_min_ago)
                    .values(status="expired")
                )
                await db.commit()
            await publish_task_event(
                task_name="expire_old_tickets",
                status="completed",
                result_key="expired_tickets_batch",
            )
        except Exception as e:
            await publish_task_event(
                task_name="expire_old_tickets",
                status="failed",
                result_key=str(e),
            )
            print(f"Error expiring tickets: {e}")
            pass

    asyncio.run(_expire())
