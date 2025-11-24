import asyncio
from datetime import datetime

from core.utils import publish_event


async def publish_task_event(task_name: str, status: str, result_key: str = ""):
    payload = {
        "task_name": task_name,
        "status": status,
        "result_key": result_key,
        "timestamp": datetime.utcnow().isoformat(),
    }
    try:
        await asyncio.to_thread(
            lambda: asyncio.run(publish_event(f"task.{task_name}", payload))
        )
    except Exception as e:
        print(f"[Celery Event Error] {task_name}: {e}")
