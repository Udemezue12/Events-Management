from celery import shared_task
from core.get_db import SyncSessionLocal
from fintechs.syncFlutterwave import FlutterwaveClient
from fintechs.syncPaystack import PaystackClient
from models.enums import PaymentMethod, PaymentStatus, TicketStatus
from models.models import Event, EventTicketType, Payment, Ticket
from sqlalchemy import update
from utils.sms_service import send_sms


@shared_task(
    name="refund_single_payment",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    acks_late=True,
)
def refund_single_payment(payment_str: str):

    db = SyncSessionLocal()
    paystack = PaystackClient()
    flutterwave = FlutterwaveClient()

    try:
        payment_id = int(payment_str)

        payment = (
            db.query(Payment)
            .filter(Payment.id == payment_id)
            .with_for_update()
            .first()
        )

        if not payment:
            return

        if payment.status == PaymentStatus.REFUNDED:
            return

        if payment.status != PaymentStatus.COMPLETED:
            return

        payment.status = PaymentStatus.REFUND_PROCESSING
        db.commit()
        if payment.payment_method == PaymentMethod.PAYSTACK:
            paystack.refund(payment.reference)
        elif payment.payment_method == PaymentMethod.FLUTTERWAVE:
            flutterwave.refund_payment(payment.transaction_id)
        else:
            raise ValueError("Unsupported payment method")

        with db.begin():

            payment = (
                db.query(Payment)
                .filter(Payment.id == payment_id)
                .with_for_update()
                .first()
            )

            if payment.status == PaymentStatus.REFUNDED:
                return

            ticket = payment.ticket

            db.execute(
                update(EventTicketType)
                .where(EventTicketType.id == ticket.ticket_type_id)
                .values(
                    sold_quantity=EventTicketType.sold_quantity - ticket.quantity,
                    total_price_gotten=EventTicketType.total_price_gotten - payment.amount,
                )
            )

            db.execute(
                update(Event)
                .where(Event.id == payment.event_id)
                .values(
                    tickets_sold=Event.tickets_sold - ticket.quantity
                )
            )

            db.execute(
                update(Ticket)
                .where(Ticket.id == payment.ticket_id)
                .values(status=TicketStatus.REFUNDED)
            )

            payment.status = PaymentStatus.REFUNDED
            db.add(payment)
        user = ticket.user
        name = f"{user.last_name} {user.first_name}"
        sms_type = "refund_processing"

        if user.phone_number:

            send_sms.sync_send_event_sms(user.phone_number, sms_type, name, ticket.event.title
                                         )
    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
