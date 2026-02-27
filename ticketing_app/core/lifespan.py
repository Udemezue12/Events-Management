import logging
from datetime import datetime, timedelta

from core.cache import cache
from core.get_db import AsyncSessionLocal
from core.ping import pinger
from core.rabbitmq import rabbitmq
from core.throttling import rate_limiter_manager
from fastapi import FastAPI
from repositories.user_repo import UserRepo
from utils.sms_service import send_sms

logger = logging.getLogger("startup")


async def lifespan(app:FastAPI):
    logger.info("Waiting for application startup...")

    try:
        await send_sms.connect()
        await send_sms.ping()
        logger.info("SMS service connected.")
    except Exception:
        logger.exception("Failed to connect to SMS service")

    try:
        await rabbitmq.connect()
        await rabbitmq.declare_queue_with_dlq("location_events")
        logger.info("RabbitMQ connected.")
    except Exception:
        logger.exception("RabbitMQ connection failed")

    try:
        async with AsyncSessionLocal() as db:
            cutoff = datetime.utcnow() - timedelta(days=7)
            auth_service = UserRepo(db)
            await auth_service.delete_expired_blacklisted_tokens(cutoff)
            logger.info("Blacklisted tokens cleanup completed.")
    except Exception:
        logger.exception("Failed to clean up blacklisted tokens")

    try:
        await cache.connect()
        logger.info("Upstash Redis connected.")
    except Exception:
        logger.exception("Upstash Redis connection failed")

    try:
        await rate_limiter_manager.connect()
        logger.info("Rate limiter connected.")
    except Exception:
        logger.exception("Rate limiter connection failed")
    # try:
    #     if os.getenv("RUN_LOCAL_PINGER", "false").lower() == "true":
    #         urls = settings.CRITICAL_SERVICE_URLS
    #         if urls and any(url.strip() for url in urls):
    #             logger.info("Starting lightweight periodic pinger...")
    #             await pinger.start()
    # except Exception:
    #     logger.exception("Failed to start lightweight periodic pinger")
    print("Application startup complete.")
    yield
    try:
        if rabbitmq.connection and not rabbitmq.connection.is_closed:
            await rabbitmq.connection.close()

        # await smtp_pool.close()

    except Exception as e:
        raise