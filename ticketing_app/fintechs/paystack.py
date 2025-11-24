import httpx
from core.settings import settings


class PaystackClient:
    BASE_URL = settings.PAYSTACK_BASE_URL

    def __init__(self):
        self.secret = settings.PAYSTACK_SECRET_KEY

    async def initialize_payment(self, email: str, amount: float, reference: str):
        url = f"{self.BASE_URL}/transaction/initialize"
        headers = {"Authorization": f"Bearer {self.secret}"}

        payload = {
            "email": email,
            "amount": int(amount * 100),
            "reference": reference
        }

        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, headers=headers)
            res.raise_for_status()
            return res.json()["data"]

    async def verify_payment(self, reference: str):
        url = f"{self.BASE_URL}/transaction/verify/{reference}"
        headers = {"Authorization": f"Bearer {self.secret}"}

        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=headers)
            res.raise_for_status()
            return res.json()["data"]

    async def refund_payment(self, reference: str):
        url = f"{self.BASE_URL}/refund"
        headers = {"Authorization": f"Bearer {self.secret}"}

        payload = {"transaction": reference}
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, headers=headers)
            res.raise_for_status()
            return res.json()
