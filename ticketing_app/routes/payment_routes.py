import logging
from typing import List

from core.breaker import breaker
from core.get_current_user import get_current_user
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.validators import validate_csrf_dependency
from core.throttling import rate_limit
from fastapi import APIRouter, Depends, HTTPException, Query
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
router = APIRouter(tags=["Payments"])


@cbv(router)
class PaymentsRoutes:
    @router.post(
        "/initalize/payment", dependencies=[rate_limit], response_model=PaymentInitOut
    )
    @safe_handler
    async def initialize_payments(
        self,
        data: PaymentInit,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency)
    ):
        async def handler():
            return await PaymentService(db).initialize_payment(
                current_user,
                ticket_id=data.ticket_id,
                method=data.method,
            )

        return await breaker.call(handler)

    @router.post(
        "/verify-payment", dependencies=[rate_limit], response_model=PaymentVerifyOut
    )
    @safe_handler
    async def verify_payments(
        self,
        reference: str,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency)
    ):
        async def handler():
            references = await PaymentService(db).verify_payment(reference=reference)
            if not references:
                raise HTTPException(status_code=404, detail="Not Found")
            return references

        return await breaker.call(handler)

    
    @router.post(
        "/refund-payments/{payment_id}",
        dependencies=[rate_limit],
        response_model=PaymentRefundOut,
    )
    @safe_handler
    async def refund_payment_endpoint(
        self,
        data: PaymentRefund,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency)
    ):
        async def handler():
            payments = await PaymentService(db).refund_payment(
                payment_id=data.payment_id,
            )
            if not payments:
                raise HTTPException(status_code=404, detail="Not Found")
            return payments

        return await breaker.call(handler)

    @router.get(
        "/organizer-payments",
        dependencies=[rate_limit],
        response_model=List[OrganizerPaymentOut],
    )
    @safe_handler
    async def organizer_payments(
        self,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency)
    ):
        async def handler():
            payments = await PaymentService(db).get_organizer_payments(
                organizer_id=current_user.id
            )
            if not payments:
                raise HTTPException(status_code=404, detail="Payments not found")
            return payments

        return await breaker.call(handler)

    @router.get(
        "/my-payments", dependencies=[rate_limit], response_model=List[UsersPaymentOut]
    )
    @safe_handler
    async def get_users_payments(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=200),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency)
    ):
        async def handler():
            payments = await PaymentService(db).get_user_payments(
                user_id=current_user.id, page=page, page_size=page_size
            )
            if not payments:
                raise HTTPException(status_code=404, detail="Payments not found")
            return payments

        return await breaker.call(handler)

    @router.get(
        "/all-payments", dependencies=[rate_limit], response_model=List[UsersPaymentOut]
    )
    @safe_handler
    async def get_all_payments(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=200),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency)
    ):
        async def handler():
            if current_user.role.name != "admin":
                raise HTTPException(status_code=403, detail="Not permitted")
            payments = await PaymentService(db).get_all_payments(
                page=page, page_size=page_size
            )
            if not payments:
                raise HTTPException(status_code=404, detail="Payments not found")
            return payments

        return await breaker.call(handler)
