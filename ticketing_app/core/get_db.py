from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.declarative import declarative_base

from .settings import settings

DATABASE_URL = settings.DATABASE_URL
RENDER_DATABASE_URL = settings.RENDER_DATABASE_URL
async_engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db_async():
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        raise
    finally:
        await session.close()


async def enable_postgis():
    async with async_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        print("PostGIS extension enabled (or already exists).")


Base = declarative_base()
