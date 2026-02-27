import logging


from core.get_db import get_db_async
from core.require_permissions import (
  
    require_organizer_and_admin_user,
)
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from models.models import User

from services.ticket_scan_service import TicketScanService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Tickets Scan and Verification"])


@cbv(router)
class TicketsRoutes:
    @router.get("/scan/ticket", dependencies=[rate_limit])
    @safe_handler
    async def scan_ticket_with_qr_code(
        self,
        qr_code: str,
        current_user: User = Depends(
            require_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):

        return await TicketScanService(db).scan_ticket_with_qr_code(qr_code=qr_code, current_user=current_user)
    @router.get("/scan/ticket_number", dependencies=[rate_limit])
    @safe_handler
    async def scan_ticket_with_ticket_number(
        self,
        ticket_number: str,
        current_user: User = Depends(
            require_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
      return await TicketScanService(db).scan_ticket_with_qr_code(ticket_number=ticket_number, current_user=current_user)
    @router.get("/verify/ticket", dependencies=[rate_limit])
    @safe_handler
    async def verify_ticket(
        self,
        ticket_number: str,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):
      return await TicketScanService(db).verify(ticket_number=ticket_number)