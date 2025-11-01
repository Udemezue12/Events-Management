from unittest.mock import AsyncMock, patch

import pytest
from app import app
from fastapi import status
from httpx import AsyncClient
from repositories.ticket_repo import TicketRepo
from services.ticket_service import TicketService


@pytest.fixture
def mock_ticket_repo():
    
    repo = AsyncMock(spec=TicketRepo)
    return repo


@pytest.fixture
def mock_ticket_service(mock_ticket_repo):
   
    service = TicketService(mock_ticket_repo)
    service.reserve_ticket = AsyncMock()
    service.mark_as_paid = AsyncMock()
    service.get_user_ticket_history = AsyncMock()
    return service


@pytest.fixture
async def async_client():
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client



@pytest.mark.asyncio
@patch("routes.tickets_routes.TicketService")
async def test_reserve_ticket_success(mock_service_class, async_client):
    
    mock_service = AsyncMock()
    mock_service.reserve_ticket.return_value = {
        "id": 1,
        "user_id": 10,
        "event_id": 100,
        "status": "reserved",
    }
    mock_service_class.return_value = mock_service

    payload = {"user_id": 10, "event_id": 100}

    response = await async_client.post("/tickets/reserve", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "reserved"
    assert data["user_id"] == 10
    assert data["event_id"] == 100
    mock_service.reserve_ticket.assert_awaited_once_with(user_id=10, event_id=100)



@pytest.mark.asyncio
@patch("routes.tickets_routes.TicketService")
async def test_pay_ticket_success(mock_service_class, async_client):
   
    mock_service = AsyncMock()
    mock_service.mark_as_paid.return_value = {
        "ticket_id": 1,
        "status": "paid",
        "message": "Ticket marked as paid successfully",
    }
    mock_service_class.return_value = mock_service

    response = await async_client.post("/1/pay")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "paid"
    assert "Ticket Paid successfully" in data["message"]
    mock_service.mark_as_paid.assert_awaited_once_with(1)



@pytest.mark.asyncio
@patch("routes.tickets_routes.TicketService")
async def test_get_user_ticket_history_success(mock_service_class, async_client):
   
    mock_service = AsyncMock()
    mock_service.get_user_ticket_history.return_value = [
        {
            "id": 1,
            "status": "paid",
            "reserved_at": "2025-11-01T00:00:00Z",
            "event_title": "Tech Summit",
            "location": "Lagos",
        }
    ]
    mock_service_class.return_value = mock_service

    response = await async_client.get("/users/10/history/tickets")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["event_title"] == "Tech Summit"
    mock_service.get_user_ticket_history.assert_awaited_once_with(10)



@pytest.mark.asyncio
@patch("routes.tickets_routes.TicketService")
async def test_get_user_ticket_history_empty(mock_service_class, async_client):
    """Should raise 404 if no ticket history found."""
    mock_service = AsyncMock()
    mock_service.get_user_ticket_history.return_value = []
    mock_service_class.return_value = mock_service

    response = await async_client.get("/users/99/history/tickets")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "No ticket history found" in response.text
