import uuid
import httpx
from core.settings import settings


class FlutterwaveClient:
    BASE_URL = settings.FLUTTERWAVE_BASE_URL

    def __init__(self):
        self.secret = settings.FLUTTERWAVE_SECRET_KEY
        self.redirect_url = settings.REDIRECT_URL

    async def initialize_payment(self, email: str, amount: float):
        url = f"{self.BASE_URL}/payments"
        headers = {"Authorization": f"Bearer {self.secret}"}
        tx_ref = f"FLW-{uuid.uuid4().hex[:12]}"

        payload = {
            "tx_ref": tx_ref,
            "amount": amount,
            "currency": "NGN",
            "redirect_url": self.redirect_url,
            "customer": {"email": email},
            "payment_options": "card",
            "customizations": {
                "title": "Test Ticket Payment",
                "description": "Payment for event ticket (sandbox)",
            },
        }

        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, headers=headers)
            res.raise_for_status()
            json_data = res.json()
            checkout_link = json_data["data"]["link"]

            return {"checkout_link": checkout_link, "tx_ref": tx_ref}

    async def verify_payment(self, tx_ref: str):
        url = f"{self.BASE_URL}/transactions"
        headers = {"Authorization": f"Bearer {self.secret}"}
        params = {"tx_ref": tx_ref}

        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=headers, params=params)
            print("Flutterwave verify status:", res.status_code)
            print("Flutterwave verify response:", res.text)

            if res.status_code != 200:
                raise ValueError(f"Flutterwave verification failed: {res.text}")

            res.raise_for_status()
            data = res.json()["data"]
            if not data:
                raise ValueError("No transaction found")
            return data[0]

    async def refund_payment(self, flw_ref: str):
        url = f"{self.BASE_URL}/transactions/{flw_ref}/refund"
        headers = {"Authorization": f"Bearer {self.secret}"}

        async with httpx.AsyncClient() as client:
            res = await client.post(url, headers=headers)
            res.raise_for_status()
            return res.json()
