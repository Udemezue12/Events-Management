from celery import Celery
from core.settings import settings


class CeleryManager:
    def __init__(self):
        self.REDIS_URL = settings.CELERY_REDIS_URL

       

        self.app = Celery(
            "ticket_tasks",
            broker=self.REDIS_URL,
            backend=self.REDIS_URL,
            include=["tasks.celery_tasks"],   
        )

        self.app.conf.update(
            task_serializer="json",
            task_track_started=True,
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            broker_connection_retry_on_startup=True,
        )

        self._register_periodic_tasks()

    def _register_periodic_tasks(self):
        @self.app.on_after_configure.connect
        def setup_periodic_tasks(sender, **kwargs):
            try:
               
                from tasks.celery_tasks import CeleryTasks
                tasks = CeleryTasks()

                sender.add_periodic_task(
                    60.0,
                    tasks.expire_reserved_tickets.s(),
                    name="expire reserved tickets every 1 minute",
                )

                print("Periodic task registered successfully.")
            except Exception as e:
                print(f"Error setting up periodic tasks: {e}")

    def task(self, *args, **kwargs):
        return self.app.task(*args, **kwargs)

    async def connect(self):
        print(f"Connecting to Celery broker: {self.REDIS_URL}")
        try:
            inspect = self.app.control.inspect()
            if inspect.ping():
                print("Celery connected successfully.")
            else:
                print("Celery connected but no workers found.")
        except Exception as e:
            print("Celery connection failed:", e)

    def delay(self, func_name: str, *args, **kwargs):
        return self.app.send_task(func_name, args=args, kwargs=kwargs)


celery_app = CeleryManager()
app = celery_app.app
