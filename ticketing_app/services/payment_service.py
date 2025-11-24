import asyncio
import uuid
from datetime import datetime

from core.breaker import breaker
from fastapi import HTTPException
from core.cache import cache
from core.utils import publish_event
from fintechs.flutterwave import FlutterwaveClient
from fintechs.paystack import PaystackClient
from models.enums import PaymentStatus
from repositories.payments_repo import PaymentRepo
from repositories.ticket_repo import TicketRepo
from sqlalchemy.ext.asyncio import AsyncSession


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.repo = PaymentRepo(db)
        self.ticket_repo = TicketRepo(db)
        self.paystack = PaystackClient()
        self.flutterwave = FlutterwaveClient()

    async def initialize_payment(self, user, ticket_id: int, method: str):
        async def handler():
            ticket = await self.ticket_repo.get_ticket_by_id(ticket_id)
            if not ticket:
                raise HTTPException(status_code=404, detail="Ticket not found")

            payment = await self.repo.create_payment(
                user_id=user.id,
                ticket=ticket,
                method=method,
                status=PaymentStatus.pending,
            )

            reference = f"PMT-{payment.id}-{uuid.uuid4().hex[:12]}"
            gateway_amount = int(payment.amount * 1)

            if method == "paystack":
                data = await self.paystack.initialize_payment(
                    email=user.email, amount=gateway_amount, reference=reference
                )
                await self.repo.set_reference(payment.id, reference)
                authorization_url = data.get("authorization_url") or data.get("link")
            elif method == "flutterwave":
                data = await self.flutterwave.initialize_payment(
                    email=user.email, amount=gateway_amount
                )
                tx_ref = str(data["tx_ref"])
                authorization_url = data["checkout_link"]
                await self.repo.set_reference(payment.id, tx_ref)
                reference = tx_ref

            else:
                raise HTTPException(status_code=400, detail="Invalid payment method")

            await cache.delete(f"user:{user.id}:payments")
            await cache.delete(f"user:{user.id}:ticket_history")
            await cache.delete("events:list")

            return {
                "payment_id": payment.id,
                "authorization_url": authorization_url,
                "reference": reference,
            }

        return await breaker.call(handler)

    async def verify_payment(self, reference: str):
        async def handler():
            payment = await self.repo.get_by_reference(reference)

            if not payment:
                raise ValueError("Payment not found")

            if payment.payment_method == "paystack":
                data = await self.paystack.verify_payment(tx_ref=reference)
                success = data.get("status") == "success"

            else:
                data = await self.flutterwave.verify_payment(reference)
                success = data["status"] == "successful"
                flw_ref = str(data["flw_ref"])
                await self.repo.set_reference(payment.id, flw_ref)

            if not success:
                raise HTTPException(
                    status_code=400, detail="Payment verification failed"
                )

            await self.repo.update_status(payment.id, PaymentStatus.completed)

            await asyncio.create_task(
                publish_event(
                    "payment.completed",
                    {
                        "payment_id": payment.id,
                        "ticket_id": payment.ticket_id,
                        "user_id": payment.user_id,
                        "amount": payment.amount,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                ),
            )

            await cache.delete(f"user:{payment.user_id}:ticket_history")
            await cache.delete(f"user:{payment.user_id}:payments")
            await cache.delete("events:list")

            return {"payment_id": payment.id, "status": "completed"}

        return await breaker.call(handler)

    async def refund_payment(self, payment_id: int):
        async def handler():
            payment = await self.repo.get_payment_by_id(payment_id)
            if not payment:
                raise ValueError("Payment not found")
            if payment.status == PaymentStatus.refunded:
                raise HTTPException(status_code=400, detail="Payment already refunded")
            if payment.status == PaymentStatus.completed:
                raise HTTPException(
                    status_code=400, detail="Only pending payments can be refunded"
                )

            if payment.payment_method == "paystack":
                await self.paystack.refund_payment(payment.reference)
            else:
                await self.flutterwave.refund_payment(payment.reference)

            await self.repo.update_status(payment.id, PaymentStatus.refunded)

            await asyncio.create_task(
                publish_event(
                    "payment.refunded",
                    {
                        "payment_id": payment.id,
                        "ticket_id": payment.ticket_id,
                        "user_id": payment.user_id,
                        "amount": payment.amount,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                ),
            )

            await cache.delete(f"user:{payment.user_id}:payments")

            return {"payment_id": payment_id, "status": "refunded"}

        return await breaker.call(handler)

    async def get_user_payments(self, user_id: int, page: int = 1, page_size: int = 50):
        async def handler():
            cache_key = f"user:{user_id}:payments:page:{page}:size:{page_size}"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached
            offset = (page - 1) * page_size
            payments = await self.repo.get_user_payments(
                user_id, offset=offset, limit=page_size
            )
            result = [payment.as_dict() for payment in payments]
            await cache.set_json(cache_key, result, ttl=300)

            await asyncio.create_task(
                publish_event(
                    "user.payments.fetched",
                    {
                        "user_id": user_id,
                        "payments_count": len(result),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                ),
            )

            return result

        return await breaker.call(handler)

    async def get_all_payments(self, page: int = 1, page_size: int = 50):
        async def handler():
            cache_key = f"admin:payments:page:{page}:size:{page_size}"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached

            offset = (page - 1) * page_size
            payments = await self.repo.get_all_payments(offset=offset, limit=page_size)
            result = [payment.as_dict() for payment in payments]

            await cache.set_json(cache_key, result, ttl=300)
            return result

        return await breaker.call(handler)

    async def get_organizer_payments(
        self, organizer_id: int, page: int = 1, page_size: int = 50
    ):
        async def handler():
            cache_key = (
                f"organizer:{organizer_id}:payments:page:{page}:size:{page_size}"
            )
            cached = await cache.get_json(cache_key)
            if cached:
                return cached
            offset = (page - 1) * page_size
            payments = await self.repo.get_payments_for_organizer(
                organizer_id, offset=offset, limit=page_size
            )
            result = [payment.as_dict(include_ids=True) for payment in payments]
            await cache.set_json(cache_key, result, ttl=300)
            return result

        return await breaker.call(handler)
