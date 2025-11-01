import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from worker.celery_tasks import expire_old_tickets
from models.models import Ticket

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mock_db(async_session):
  
    now = datetime.utcnow()
    old_ticket = Ticket(
        id=1,
        user_id=1,
        event_id=1,
        status="reserved",
        created_at=now - timedelta(minutes=3)
    )
    recent_ticket = Ticket(
        id=2,
        user_id=2,
        event_id=2,
        status="reserved",
        created_at=now - timedelta(seconds=30)
    )
    async_session.add_all([old_ticket, recent_ticket])
    await async_session.commit()
    return async_session


@pytest.fixture
def mock_publish_event():
   
    with patch("worker.celery_tasks.publish_task_event", new_callable=AsyncMock) as mock:
        yield mock


@pytest.mark.asyncio
async def test_expire_old_tickets_expires_old_reservations(mock_db, mock_publish_event):
   
    with patch("worker.celery_tasks.AsyncSessionLocal", return_value=mock_db):
        await asyncio.to_thread(expire_old_tickets)

    result = (await mock_db.execute(
        Ticket.__table__.select()
    )).fetchall()

    statuses = {row.status for row in result}
    assert "expired" in statuses
    assert any(r.status == "reserved" for r in result), "Recent tickets must remain reserved"

    mock_publish_event.assert_awaited_with(
        task_name="expire_old_tickets",
        status="completed",
        result_key="expired_tickets_batch"
    )


@pytest.mark.asyncio
async def test_expire_old_tickets_handles_db_error(mock_db, mock_publish_event):
   
    async def broken_execute(*args, **kwargs):
        raise Exception("DB error")

    mock_db.execute = broken_execute

    with patch("worker.celery_tasks.AsyncSessionLocal", return_value=mock_db):
        await asyncio.to_thread(expire_old_tickets)

    mock_publish_event.assert_awaited_with(
        task_name="expire_old_tickets",
        status="failed",
        result_key="DB error"
    )
