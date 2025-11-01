import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models.models import Base
from core.settings import settings



@pytest.fixture(scope="session")
async def async_engine():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def async_session(async_engine):
    async_session_maker = sessionmaker(
        async_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with async_session_maker() as session:
        yield session
