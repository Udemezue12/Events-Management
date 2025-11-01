
import datetime

from core.rabbitmq import rabbitmq
from core.settings import settings


async def publish_task_event(task_name: str, status: str, result_key: str):
   
    data = {
        "task": task_name,
        "status": status,
        "result_key": result_key,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }

    await rabbitmq.publish_json(
        exchange_name=settings.RABBITMQ_MAIN_EXCHANGE,
        routing_key="task.completed",
        data=data,
    )
