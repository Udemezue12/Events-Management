
from .rabbitmq import rabbitmq
from core.settings import settings





async def publish_event(event_name: str, data: dict):
    await rabbitmq.publish_json(
        exchange_name=settings.RABBITMQ_MAIN_EXCHANGE,
        routing_key=event_name,
        data=data,
    )