from core.setup_gdal import setup_gdal

setup_gdal()  # Only use it in development
import asyncio
import logging
import os
from pathlib import Path

import uvicorn
from core.csrf_middleware import AutoRefreshAccessTokenMiddleware
from core.get_csfToken import csrf_router
from core.settings import settings
from core.throttling import rate_limiter_manager
from dotenv import load_dotenv
from fastapi import FastAPI
from core.lifespan import lifespan
from fastapi.responses import HTMLResponse
from routes.event_routes import router as event_router
from routes.payment_routes import router as payment_router
from routes.review_routes import router as review_router
from routes.ticket_routes import router as ticket_router
from routes.user_routes import router as user_router
from routes.venue_routes import router as venue_router
from starlette.middleware.sessions import SessionMiddleware
from routes.event_ticket_routes import rouuter as event_ticket_router
from routes.ticket_scan_routes import router as ticket_scanning_router
load_dotenv()
logging.basicConfig(level=logging.INFO)
app = FastAPI(
    title=settings.PROJECT_NAME,
    exception_handlers={429: rate_limiter_manager.limit_exceeded_handler},
    version="2.0.0",
    lifespan=lifespan
)
BASE_DIR = Path(__file__).resolve().parent


app.include_router(csrf_router, prefix="/v2")
app.include_router(user_router, prefix="/v2")
app.include_router(event_ticket_router, prefix="/v2")
app.include_router(ticket_router, prefix="/v2")
app.include_router(ticket_scanning_router, prefix="/v2")
app.include_router(event_router, prefix="/v2")
app.include_router(venue_router, prefix="/v2")
app.include_router(payment_router, prefix="/v2")
app.include_router(review_router, prefix="/v2")


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok"}



    

    

   





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
