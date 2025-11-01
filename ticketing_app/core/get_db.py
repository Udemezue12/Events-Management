import ssl
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .settings import settings

# ---------------------------------------------
# ✅ SYNC ENGINE (for Alembic / Django / Scripts)
# ---------------------------------------------
SyncEngine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=SyncEngine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------
# ✅ ASYNC ENGINE (for FastAPI / AsyncORM)
# ---------------------------------------------
ssl_context = ssl.create_default_context(cafile=settings.SUPABASE_CA_PATH)
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED

AsyncEngine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
   
)

AsyncSessionLocal = async_sessionmaker(
    bind=AsyncEngine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db_async():
    async with AsyncSessionLocal() as session:
        yield session


Base = declarative_base()
