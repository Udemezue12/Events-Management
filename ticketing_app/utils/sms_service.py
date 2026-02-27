import httpx
from core.settings import settings
from core.sms_breaker import sms_breaker as breaker


class TermiiClient:
    def __init__(self):
        self.base_url = settings.TERMII_BASE_URL
        self.api_key = settings.TERMII_API_KEY
        self.async_client: httpx.AsyncClient | None = None
        self.sync_client: httpx.Client | None = None

    def sync_connect(self):
        self.sync_client = httpx.Client(
            base_url=self.base_url,
            timeout=10,
        )

    def sync_close(self):
        if self.sync_client:
            self.sync_client.close()

    async def async_connect(self):
        self.async_client = httpx.AsyncClient(
            base_url=self.base_url, timeout=10)

    async def async_close(self):
        if self.async_client:
            await self.async_client.aclose()

    async def ping(self):
        if not self.async_client:
            raise RuntimeError("Termii client not connected")

    async def send_sms(
        self,
        to: str,
        otp: str | None = None,
        message: str | None = None,
        name: str | None = None,
        sender_id=settings.TERMII_SENDER_ID,
    ):
        try:
            async def _handler():
                await self.async_connect()
                if not message:
                    if name:
                        messages = (
                            f"Hello {name}, your OTP is {otp}. "
                            "This code expires in 5 minutes. Do not share it with anyone."
                        )
                    else:
                        messages = (
                            f"Your OTP is {otp}. "
                            "This code expires in 5 minutes. Do not share it with anyone."
                        )
                else:
                    messages = message

                payload = {
                    "to": to,
                    "from": sender_id,
                    "sms": messages,
                    "type": "plain",
                    "channel": "generic",
                    "api_key": self.api_key,
                }

                if not self.async_client:
                    raise RuntimeError("Termii client not connected")

                response = await self.async_client.post("/api/sms/send", json=payload)
                return response.json()
            return await breaker.async_call(_handler)
        finally:
            await self.async_close()

    def sync_send_event_sms(
        self,
        to: str,
        sms_type: str,
        name: str | None = None,
        event_name: str | None = None,
        ticket_id: int | None = None,

        sender_id=settings.TERMII_SENDER_ID,
    ):

        try:
            self.sync_connect()

            if not self.sync_client:
                raise RuntimeError("Termii client not connected")

            if sms_type == "ticket_expired":
                message = (
                    f"Hello {name}, your reserved ticket with id {ticket_id} has expired."
                    if name
                    else f"Hello, your reserved ticket with id {ticket_id} has expired."
                )
                message += "\n\nPlease book again if you are still interested."
            elif sms_type == "ticket_reserved":
                message = (
                    f"Hello {name}, you have successfuly booked and reserved this ticket for this {event_name}, you have less than 12hrs pay or it will be canceled "
                    if name
                    else "Hello,you have successfuly booked and reserved this ticket, you have less than 12hrs pay or it will be canceled."
                )
                message += "\n\nPlease try and pay as early as possible."

            elif sms_type == "payment_success":
                message = (
                    f"Hello {name}, your payment was successful."
                    if name
                    else "Hello, your payment was successful."
                )

                if event_name:
                    message += f"\nEvent: {event_name}"

                message += "\n\nYour ticket has been confirmed."

            elif sms_type == "refund_processing":
                message = (
                    f"Hello {name}, your refund is being processed."
                    if name
                    else "Hello, your refund is being processed."
                )

                if event_name:
                    message += f"\nEvent: {event_name}"

                message += "\n\nThe event was cancelled. Funds will reflect shortly."

            else:
                raise ValueError("Invalid sms_type provided")

            payload = {
                "to": to,
                "from": sender_id,
                "sms": message,
                "type": "plain",
                "channel": "generic",
                "api_key": self.api_key,
            }

            def _handler():
                response = self.sync_client.post("/api/sms/send", json=payload)
                return response.json()
            return breaker.sync_call(_handler)

        finally:
            self.sync_close()


send_sms = TermiiClient()
