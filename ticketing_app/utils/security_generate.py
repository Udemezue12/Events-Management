import secrets
from random import randint

from core.breaker import breaker
from itsdangerous import URLSafeTimedSerializer
from core.settings import settings
from redis.asyncio import Redis

reset_serializer = URLSafeTimedSerializer(settings.RESET_SECRET_KEY)
verify_serializer = URLSafeTimedSerializer(settings.VERIFY_EMAIL_SECRET_KEY)

redis = Redis.from_url(settings.CELERY_REDIS_URL, decode_responses=True)


class UserGenerate:
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
