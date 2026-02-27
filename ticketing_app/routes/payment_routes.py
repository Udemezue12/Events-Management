import logging
from typing import List

from core.breaker import breaker
from core.get_current_user import get_current_user
from core.get_db import get_db_async
from core.require_permissions import (
    require_admin_user,
    require_attendee_organizer_and_admin_user,
    require_organizer_and_admin_user,
)
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from fastapi import APIRouter, Depends,  Query
from fastapi_utils.cbv import cbv
from models.models import User
from schemas.schema import (
    OrganizerPaymentOut,
    PaymentInit,
    PaymentInitOut,
    PaymentRefund,
    PaymentRefundOut,
    PaymentVerifyOut,
    UsersPaymentOut,
)
from services.payment_service import PaymentService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Tickets"])


@cbv(router)
class PaymentsRoutes:
    @router.post(
        "/{ticked_id}/pay", dependencies=[rate_limit], response_model=PaymentInitOut
    )
    @safe_handler
    async def initialize_payments(
        self,
        data: PaymentInit,
        current_user: User = Depends(
            require_attendee_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):

        return await PaymentService(db).initialize_payment(
            current_user,
            ticket_id=data.ticket_id,
            method=data.method,
        )

    @router.post(
        "/{reference}/verify-payment", dependencies=[rate_limit], response_model=PaymentVerifyOut
    )
    @safe_handler
    async def verify_payments(
        self,
        reference: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):

        return await PaymentService(db).verify_payment(reference=reference)

    @router.post(
        "/{payment_id}/refund",
        dependencies=[rate_limit],
        response_model=PaymentRefundOut,
    )
    @safe_handler
    async def refund_payment_endpoint(
        self,
        payment_id: int,
        current_user: User = Depends(require_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):

        return await PaymentService(db).refund_payment(
            payment_id=payment_id,
        )

    @router.get(
        "/organizer-payments",
        dependencies=[rate_limit],
        response_model=List[OrganizerPaymentOut],
    )
    @safe_handler
    async def organizer_payments(
        self,
        current_user: User = Depends(require_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):

        return await PaymentService(db).get_organizer_payments(
            organizer_id=current_user.id
        )

    @router.get(
        "/my-payments", dependencies=[rate_limit], response_model=List[UsersPaymentOut]
    )
    @safe_handler
    async def get_users_payments(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=200),
        current_user: User = Depends(
            require_attendee_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):

        return await PaymentService(db).get_user_payments(
            user_id=current_user.id, page=page, page_size=page_size
        )

    @router.get(
        "/all-payments", dependencies=[rate_limit], response_model=List[UsersPaymentOut]
    )
    @safe_handler
    async def get_all_payments(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=200),
        current_user: User = Depends(require_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):

        return await PaymentService(db).get_all_payments(
            page=page, page_size=page_size
        )
