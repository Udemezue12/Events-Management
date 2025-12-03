# from core.setup_gdal import setup_gdal

# setup_gdal()  # Only use it in development
import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import uvicorn
from core.cache import cache
from core.csrf_middleware import AutoRefreshAccessTokenMiddleware
from core.get_csfToken import csrf_router
from core.get_db import AsyncSessionLocal
from core.ping import pinger
from core.rabbitmq import rabbitmq
from core.settings import settings
from core.throttling import rate_limiter_manager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from repositories.user_repo import UserRepo
from routes.event_routes import router as event_router
from routes.payment_routes import router as payment_router
from routes.review_routes import router as review_router
from routes.ticket_routes import router as ticket_router
from routes.user_routes import router as user_router
from routes.venue_routes import router as venue_router
from starlette.middleware.sessions import SessionMiddleware
from utils.sms_service import send_sms

load_dotenv()
logger = logging.getLogger("startup")
logging.basicConfig(level=logging.INFO)
app = FastAPI(
    title=settings.PROJECT_NAME,
    exception_handlers={429: rate_limiter_manager.limit_exceeded_handler},
    version="2.0.0",
)
BASE_DIR = Path(__file__).resolve().parent


app.include_router(csrf_router)
app.include_router(user_router)
app.include_router(ticket_router)
app.include_router(event_router)
app.include_router(venue_router)
app.include_router(payment_router)
app.include_router(review_router)


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
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

    try:
        if os.getenv("RUN_LOCAL_PINGER", "false").lower() == "true":
            urls = settings.CRITICAL_SERVICE_URLS
            if urls and any(url.strip() for url in urls):
                logger.info("Starting lightweight periodic pinger...")
                asyncio.create_task(pinger.start())
    except Exception:
        logger.exception("Failed to start lightweight periodic pinger")

    logger.info("Application startup complete.")


@app.on_event("shutdown")
async def shutdown_event():
    if rabbitmq.connection and not rabbitmq.connection.is_closed:
        await rabbitmq.connection.close()


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.add_middleware(
    AutoRefreshAccessTokenMiddleware,
    secret_key=settings.SECRET_KEY,
    algorithm=settings.ALGORITHM,
    access_exp_minutes=settings.ACCESS_EXPIRE_MINUTES,
    secure_cookies=settings.SECURE_COOKIES,
    skip_paths={
        "/docs",
        "/redoc",
        "/openapi.json",
        "/logout",
        "/api/auth/logout",
        "/health",
        "/static",
    },
)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=True)
