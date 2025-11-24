import asyncio
from datetime import datetime, timedelta

from core.get_db import AsyncSessionLocal
from models.models import Ticket
from sqlalchemy import update
from worker.celery_app import app, celery_app
from worker.celery_events import publish_task_event


class CeleryTasks:
    
    @app.on_after_configure.connect
    def setup_periodic_tasks(self, sender, **kwargs):
        try:
            sender.add_periodic_task(
                60.0,
                self.expire_tickets_task.s(),
                name="expire reserved tickets every 1 minute",
            )
        except Exception as e:
            print(f"Error setting up periodic tasks: {e}")
            pass

    async def expire_reserved_tickets(self, ):
        async with AsyncSessionLocal() as db:
            try:
                two_min_ago = datetime.utcnow() - timedelta(minutes=2)

                stmt = (
                    update(Ticket)
                    .where(Ticket.status == "reserved")
                    .where(Ticket.created_at < two_min_ago)
                    .values(status="expired")
                )

                await db.execute(stmt)
                await db.commit()

                await publish_task_event(
                    task_name="expire_reserved_tickets",
                    status="completed",
                    result_key="expired_tickets_batch",
                )

            except Exception as e:
                await publish_task_event(
                    task_name="expire_reserved_tickets",
                    status="failed",
                    result_key=str(e),
                )
                print(f"[Celery Task Error] expire_reserved_tickets: {e}")

    @celery_app.task(name="tasks.expire_tickets")
    def expire_tickets_task(self):
        asyncio.run(self.expire_reserved_tickets())


tasks_app = CeleryTasks()