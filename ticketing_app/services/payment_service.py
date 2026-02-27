
import uuid
from datetime import datetime
from worker.celery_app import app as task_app
from core.breaker import breaker
from fastapi import HTTPException, BackgroundTasks
from utils.sms_service import send_sms
from core.cache import cache
from core.utils import publish_event
from fintechs.flutterwave import FlutterwaveClient
from fintechs.paystack import PaystackClient
from models.enums import PaymentStatus, TicketStatus
from repositories.payments_repo import PaymentRepo
from repositories.user_repo import UserRepo
from repositories.ticket_repo import TicketRepo
from repositories.event_repo import EventRepo
from sqlalchemy.ext.asyncio import AsyncSession
from models.enums import PaymentMethod, Role, PaymentStatus, TicketStatus
from repositories.event_ticket_repo import EventTicketRepo
from decimal import Decimal
from services.generate_multipe_tickets import GenerateMultipleTicketService
from core.redis_idempotency import RedisIdempotency
from repositories.event_ticket_repo import EventTicketRepo
from collections import defaultdict
from core.settings import settings

class PaymentService:
    START_LOCK_KEY = "payment-start-lock"
    VERIFY_LOCK_KEY = "payment-verify-lock"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo: UserRepo = UserRepo(db)
        self.multiple_tickets = GenerateMultipleTicketService(db)
        self.event_ticket_repo: EventTicketRepo = EventTicketRepo(db)
        self.redis_idempotency = RedisIdempotency(startup="payment_service")
        self.event_repo: EventRepo = EventRepo(db)
        self.repo = PaymentRepo(db)
        self.ticket_repo = TicketRepo(db)
        self.paystack = PaystackClient()
        self.flutterwave = FlutterwaveClient()

    async def payment_options(
        self,
        data,
        gateway_amount,
        current_user,
        payment,
    ) -> dict:
        reference = f"PMT-{payment.id.hex}-{uuid.uuid4().hex[:12]}"
        callback_url = (
            f"{settings.FRONTEND_URL}/payment-callback.html?reference={reference}"
        )

        if data.payment_method == PaymentMethod.PAYSTACK:
            paystack_data = await self.paystack.initialize_payment(
                email=current_user.email,
                amount=gateway_amount,
                reference=reference,
                callback_url=callback_url,
            )
            await self.repo.set_reference(payment.id, reference)
            authorization_url = paystack_data.get(
                "authorization_url"
            ) or paystack_data.get("link")
        elif data.payment_method == PaymentMethod.FLUTTERWAVE:
            flutterwave_data = await self.flutterwave.initialize_payment(
                email=current_user.email,
                amount=gateway_amount,
                redirect_url=callback_url,
                reference=reference,
            )
            tx_ref = str(flutterwave_data["tx_ref"])
            authorization_url = flutterwave_data["checkout_link"]
            await self.repo.set_reference(payment.id, tx_ref)
            reference = tx_ref

        else:
            raise HTTPException(
                status_code=400, detail="Invalid payment method")
        return {
            "payment_id": str(payment.id),
            "authorization_url": authorization_url,
            "reference": reference,
        }

    async def initialize_payment(self, event_id: int, current_user, data):

        async def _start():

            user = await self.user_repo.get_by_id(user_id=current_user.id)

            if not user:
                raise HTTPException(404, "User not found")

            if user.role == Role.ADMIN:
                raise HTTPException(
                    400, "You are an admin, so you cannot make a payment"
                )

            event = await self.event_repo.get_by_id(event_id)
            if not event or not event.is_active:
                raise HTTPException(
                    404, "Event not found or no longer active"
                )

           
            reserved_tickets = await self.ticket_repo.get_user_reserved_tickets(
                user_id=user.id,
                event_id=event_id
            )

            if not reserved_tickets:
                raise HTTPException(404, "No reserved tickets found")

            grouped = defaultdict(list)
            for ticket in reserved_tickets:
                grouped[ticket.ticket_type_id].append(ticket)

            total_amount = 0
            total_quantity = len(reserved_tickets)

            async with self.db.begin():

                payment = await self.repo.create_payment(
                    user_id=user.id,
                    event_id=event_id,
                    quantity=total_quantity,
                    method=data.method,
                    status=PaymentStatus.PENDING,
                )

                for ticket_type_id, tickets in grouped.items():

                    quantity = len(tickets)
                    unit_price = tickets[0].ticket_type.price
                    total_price = unit_price * quantity

                    total_amount += total_price

                    await self.repo.create_payment_item(
                        payment_id=payment.id,
                        ticket_type_id=ticket_type_id,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price
                    )

                payment.total_amount = total_amount

            

            await cache.delete_cache_keys_async(
                f"user:{user.id}:payments",
                f"user:{user.id}:ticket_history",
                "events:list"
            )

            gateway_amount = int(total_amount * 100)

            return await self.payment_options(
                data=data,
                gateway_amount=gateway_amount,
                current_user=current_user,
                payment=payment,
            )

        return await self.redis_idempotency.run_once(
            key=f"{self.START_LOCK_KEY}:{current_user.id}:{event_id}",
            coro=_start,
        )

    async def verify_payment(self, reference: str, background_tasks: BackgroundTasks):
        async def _start():

            payment = await self.repo.get_by_reference(reference)

            if not payment:
                raise HTTPException(404, "Payment not found")
            if payment.status == PaymentStatus.COMPLETED:
                raise HTTPException(400, "Already Completed and Verified")
            if payment.status == PaymentStatus.REFUNDED:
                raise HTTPException(400, "This Payment has been refunded")
            success = False
            flw_ref = None

            if payment.payment_method == PaymentMethod.PAYSTACK:
                data = await self.paystack.verify_payment(tx_ref=reference)
                success = data.get("status") == "success"
                if success:
                    transaction_id = str(data["transaction_id"])
                    await self.repo.set_transaction_id(payment.id, transaction_id)

            elif payment.payment_method == PaymentMethod.FLUTTERWAVE:
                data = await self.flutterwave.verify_payment(reference)
                success = data.get("success") is True
                if success:
                    flw_ref = data["flw_ref"]
                    transaction_id = str(data["transaction_id"])

                    await self.repo.set_reference(payment.id, flw_ref)
                    await self.repo.set_transaction_id(payment.id, transaction_id)
            else:
                raise HTTPException(404, "No payment provider was found")

            if not success:
                await self.repo.update_status(
                    payment_id=payment.id,
                    status=PaymentStatus.VERIFICATION_PENDING)
                task_app.send_task(
                    "retry_verify_payment",
                    args=[reference],
                )
                raise HTTPException(
                    status_code=400, detail="Payment verification retrying"
                )
            async with self.db.begin():

                tickets = await self.ticket_repo.get_reserved_tickets_for_update(
                    user_id=payment.user_id,
                    event_id=payment.event_id,
                    quantity=payment.ticket_quantity
                )

                if len(tickets) != payment.ticket_quantity:
                    raise HTTPException(
                        400,
                        "Reserved tickets mismatch or expired"
                    )

                total_price_increment = 0
                
                ticket_type_id = tickets[0].ticket_type_id
                event_id = tickets[0].event_id

                for ticket in tickets:
                    ticket.status = TicketStatus.SOLD
                    ticket.payment_id = payment.id
                    total_price_increment += ticket.price_paid

                await self.event_ticket_repo.get_total_price_sold(
                    ticket_type_id=ticket_type_id,
                    price_paid=total_price_increment,

                )

                await self.event_repo.increment_event_tickets_sold(
                    event_id=event_id,
                    quantity=len(tickets),

                )

                await self.repo.update_status(payment.id, PaymentStatus.COMPLETED)

            for ticket in tickets:
                task_app.send_task(
                    "generate_ticket_pass",
                    args=[str(ticket.id)]
                )

            user = tickets[0].user
            name = f"{user.last_name} {user.first_name}"
            sms_type = "payment_success"

            if user.phone_number:
                background_tasks.add_task(
                    send_sms.sync_send_event_sms,
                    user.phone_number,
                    sms_type,
                    name,
                    tickets[0].event.title,
                )

            await publish_event(
                "payment.completed",
                {
                    "payment_id": payment.id,
                    "user_id": payment.user_id,
                    "amount": payment.total_amount,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            await cache.delete_cache_keys_async(
                f"user:{payment.user_id}:ticket_history",
                f"user:{payment.user_id}:payments",
                "events:list",
            )

            return {"payment_id": payment.id, "status": "completed"}

        return await self.redis_idempotency.run_once(
            key=f"{self.VERIFY_LOCK_KEY}:{reference}",
            coro=_start,
        )

    async def refund_payment(self, payment_id: int):

        payment = await self.repo.get_payment_by_id(payment_id)
        if not payment:
            raise ValueError("Payment not found")
        if payment.status == PaymentStatus.REFUNDED:
            raise HTTPException(
                status_code=400, detail="Payment already refunded")
        if payment.status == PaymentStatus.COMPLETED:
            raise HTTPException(
                status_code=400, detail="Only pending payments can be refunded"
            )

        if payment.payment_method == PaymentMethod.PAYSTACK:
            await self.paystack.refund(payment.reference)
        else:
            await self.flutterwave.refund_payment(payment.transaction_id)

        await self.repo.update_status(payment.id, PaymentStatus.REFUNDED)

        await publish_event(
            "payment.refunded",
            {
                "payment_id": payment.id,
                "ticket_id": payment.ticket_id,
                "user_id": payment.user_id,
                "amount": payment.amount,
                "timestamp": datetime.utcnow().isoformat(),
            },
        ),

        await cache.async_delete(f"user:{payment.user_id}:payments")

        return {"payment_id": payment_id, "status": "refunded"}

    async def get_user_payments(self, user_id: int, page: int = 1, page_size: int = 50):
        async def handler():
            cache_key = f"user:{user_id}:payments:page:{page}:size:{page_size}"
            cached = await cache.async_get_json(cache_key)
            if cached:
                return cached
            offset = (page - 1) * page_size
            payments = await self.repo.get_user_payments(
                user_id, offset=offset, limit=page_size
            )
            result = [payment.as_dict() for payment in payments]
            if not result:
                return []
            await cache.async_set_json(cache_key, result, ttl=300)

            await publish_event(
                "user.payments.fetched",
                {
                    "user_id": user_id,
                    "payments_count": len(result),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            ),

            return result

    async def get_all_payments(self, page: int = 1, page_size: int = 50):

        cache_key = f"admin:payments:page:{page}:size:{page_size}"
        cached = await cache.async_get_json(cache_key)
        if cached:
            return cached

        offset = (page - 1) * page_size
        payments = await self.repo.get_all_payments(offset=offset, limit=page_size)
        result = [payment.as_dict() for payment in payments]
        if not result:
            return []

        await cache.async_set_json(cache_key, result, ttl=300)
        return result

    async def get_organizer_payments(
        self, organizer_id: int, page: int = 1, page_size: int = 50
    ):

        cache_key = (
            f"organizer:{organizer_id}:payments:page:{page}:size:{page_size}"
        )
        cached = await cache.async_get_json(cache_key)
        if cached:
            return cached
        offset = (page - 1) * page_size
        payments = await self.repo.get_payments_for_organizer(
            organizer_id, offset=offset, limit=page_size
        )
        result = [payment.as_dict(include_ids=True)
                  for payment in payments]
        if not result:
            return []
        await cache.async_set_json(cache_key, result, ttl=300)
        return result
