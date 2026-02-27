import time

from fintechs.syncFlutterwave import FlutterwaveClient
from fintechs.syncPaystack import PaystackClient
from models.enums import PaymentMethod, PaymentStatus, TicketStatus
from repositories.event_repo import EventRepo
from repositories.event_ticket_repo import EventTicketRepo
from repositories.payments_repo import PaymentRepo
from repositories.ticket_repo import TicketRepo
from repositories.user_repo import UserRepo
from tasks.generate_ticket_pass_tasks import generate_ticket_pass_tasks
from utils.sms_service import send_sms

from sqlalchemy.orm import Session as SyncSession


class PaymentRetry:
    def __init__(self, db: SyncSession):
        self.db = db
        self.user_repo = UserRepo(db)
        self.paystack = PaystackClient()
        self.flutterwave = FlutterwaveClient()
        self.repo = PaymentRepo(db)
        self.event_repo = EventRepo(db)
        self.ticket_repo = TicketRepo
        self.event_ticket_repo: EventTicketRepo = EventTicketRepo(db)

    def run_retry(self, reference: str):
        payment = self.repo.sync_get_reference(reference)

        if not payment:
            return

        if payment.status == PaymentStatus.COMPLETED:
            return
        if payment.status == PaymentStatus.REFUNDED:
            return

        retries = 3
        base_delay = 5

        for attempt in range(retries):
            try:
                if payment.payment_method == PaymentMethod.PAYSTACK:
                    data = self.paystack.verify_payment(reference)
                    success = data.get("success") is True
                    if success:
                        transaction_id = str(data["transaction_id"])
                        self.repo.sync_set_transaction_id(
                            payment.id, transaction_id)

                else:
                    data = self.flutterwave.verify_payment(reference)
                    success = data.get("success") is True
                    if success:
                        flw_ref = data["flw_ref"]
                        transaction_id = str(data["transaction_id"])

                        self.repo.sync_set_reference(payment.id, flw_ref)
                        self.repo.sync_set_transaction_id(
                            payment.id, transaction_id)

                if data.get("success"):

                    with self.db.begin():

                        tickets = self.ticket_repo.sync_get_reserved_tickets_for_update(
                            user_id=payment.user_id,
                            event_id=payment.event_id,
                            quantity=payment.ticket_quantity
                        )

                        if len(tickets) != payment.ticket_quantity:
                            raise ValueError(
                                "Reserved tickets mismatch or expired"
                            )

                        total_price_increment = 0

                        ticket_type_id = tickets[0].ticket_type_id
                        event_id = tickets[0].event_id

                        for ticket in tickets:
                            ticket.status = TicketStatus.SOLD
                            ticket.payment_id = payment.id
                            total_price_increment += ticket.price_paid

                        self.event_ticket_repo.sync_get_total_price_sold(
                            ticket_type_id=ticket_type_id,
                            price_paid=total_price_increment,

                        )

                        self.event_repo.sync_increment_event_tickets_sold(
                            event_id=event_id,
                            quantity=len(tickets),

                        )

                        self.repo.sync_update_status(
                            payment.id, PaymentStatus.COMPLETED)

                    for ticket in tickets:
                        generate_ticket_pass_tasks.delay(
                            args=[str(ticket.id)]
                        )

                    user = tickets[0].user
                    name = f"{user.last_name} {user.first_name}"
                    sms_type = "payment_success"

                    if user.phone_number:

                        send_sms.sync_send_event_sms(
                            user.phone_number,
                            sms_type,
                            name,
                            tickets[0].event.title,
                        )

                return

            except Exception as e:
                print(f"Retry attempt failed: {e}")
                pass

            sleep_time = base_delay * (2**attempt)
            time.sleep(sleep_time)

        try:
            if payment.payment_method == PaymentMethod.PAYSTACK:
                self.paystack.refund(reference)
            elif payment.payment_method == PaymentMethod.FLUTTERWAVE:
                self.flutterwave.refund_payment(payment.transaction_id)

            self.repo.sync_update_status(
                payment_id=payment.id,
                status=PaymentStatus.REFUNDED,
            )

            

        except Exception as e:
            print(f"Refund failed: {e}")
            self.repo.sync_update_status(
                payment.id,
                PaymentStatus.FAILED,
            )
