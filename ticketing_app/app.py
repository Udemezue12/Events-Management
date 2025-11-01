from core.setup_gdal import setup_gdal

setup_gdal()


from pathlib import Path

import uvicorn
from core.cache import cache
from core.rabbitmq import rabbitmq
from core.settings import settings
from core.throttling import rate_limiter_manager
from dotenv import load_dotenv
from fastapi import FastAPI

from fastapi.responses import FileResponse
from passlib.context import CryptContext
from routes.event_routes import router as event_router
from routes.ticket_routes import router as ticket_router
from routes.user_routes import router as user_router
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()

app = FastAPI(
    title=settings.PROJECT_NAME,
    exception_handlers={429: rate_limiter_manager.limit_exceeded_handler},
    description=f"This is the backend for the {settings.PROJECT_NAME} built with FastAPI.",
    version="1.0.0",
   
)
BASE_DIR = Path(__file__).resolve().parent



app.include_router(ticket_router)
app.include_router(event_router)
app.include_router(user_router)





@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    print("INFO:Waiting for application startup.")

    try:
        print(" Connecting to RabbitMQ...")
        await rabbitmq.connect()
        await rabbitmq.declare_queue_with_dlq("location_events")
        print("Connected to RabbitMQ.")
    except Exception as e:
        print(f"RabbitMQ connection failed: {e}")

    try:
        print("Connecting to Upstash Redis...")
        await cache.connect()
        print("Connected to Upstash Redis.")
    except Exception as e:
        print(f"Upstash Redis connection failed: {e}")
    try:
        print("Connecting to Redis Cloud for rate limiting...")
        await rate_limiter_manager.connect()
        print("Rate limiter (Redis Cloud) connected.")
    except Exception as e:
        print(f"Rate limiter connection failed: {e}")
    

    print("Application startup complete.")


@app.on_event("shutdown")
async def shutdown_event():
    if rabbitmq.connection and not rabbitmq.connection.is_closed:
        await rabbitmq.connection.close()


@app.get("/")
async def read_index():
    try:
        index_path = BASE_DIR.parent / "frontend" / "build" / "index.html"

        if not index_path.exists():
            return {"detail": "index.html not found."}

        return FileResponse(index_path)

    except Exception as e:
        return {"detail": f"Error serving index.html: {str(e)}"}



app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=True)
