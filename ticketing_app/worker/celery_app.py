from celery import Celery
from celery.schedules import crontab
from core.settings import settings


class CeleryManager:
    def __init__(self):
        self.REDIS_URL = settings.CELERY_REDIS_URL

        self.app = Celery(
            "ticket_tasks",
            broker=self.REDIS_URL,
            backend=self.REDIS_URL,
            include=["core.celery_tasks"],
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

    def task(self, *args, **kwargs):
        try:
            return self.app.task(*args, **kwargs)
        except Exception as e:
            print(f"Error occurred while registering task: {e}")

    async def connect(self):
        print(f"Connecting to Celery broker: {self.REDIS_URL}")
        try:
            inspect = self.app.control.inspect()
            if inspect.ping():
                print("Celery connected successfully.")
            else:
                print("Celery connected but no workers found.")
        except Exception as e:
            print("Celery connection failed:", exc_info=e)

    def delay(self, func_name: str, *args, **kwargs):
        try:
            return self.app.send_task(func_name, args=args, kwargs=kwargs)
        except Exception as e:
            print(f"Error occurred while delaying task {func_name}: {e}")


celery_app = CeleryManager()
app = celery_app.app


from core import celery_tasks
