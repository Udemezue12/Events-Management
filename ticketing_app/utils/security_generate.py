import secrets
from random import randint

from core.breaker import breaker
from itsdangerous import URLSafeTimedSerializer
from core.settings import settings
from redis.asyncio import Redis
import random
import string
from datetime import datetime
import qrcode
import os

reset_serializer = URLSafeTimedSerializer(settings.RESET_SECRET_KEY)
verify_serializer = URLSafeTimedSerializer(settings.VERIFY_EMAIL_SECRET_KEY)

redis = Redis.from_url(settings.CELERY_REDIS_URL, decode_responses=True)


class UserGenerate:

    def generate_qr(self, ticket_number: str):
        qr_data = f"https://yourdomain.com/verify-ticket/{ticket_number}"

        qr = qrcode.make(qr_data)

        file_path = f"media/qrcodes/{ticket_number}.png"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        qr.save(file_path)

        return file_path

    def generate_ticket_number(self, ticket_id: int) -> str:
        year = datetime.utcnow().year
        random_code = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=4))
        return f"EVT-{year}-{ticket_id:06d}-{random_code}"

    async def generate_csrf_token(self) -> str:
        return secrets.token_hex(32)

    async def generate_verify_token(self, email: str) -> str:
        return verify_serializer.dumps(email, salt=settings.VERIFY_EMAIL_SALT)

    async def generate_reset_token(self, email: str) -> str:
        return reset_serializer.dumps(email, salt=settings.RESET_PASSWORD_SALT)

    async def generate_otp(self, email: str) -> str:
        async def handler():
            otp = str(randint(100000, 999999))
            await redis.setex(f"otp:{email}", 300, otp)
            return otp

        return await breaker.call(handler)


user_generate = UserGenerate()
