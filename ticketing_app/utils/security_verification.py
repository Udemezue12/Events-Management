from core.breaker import breaker
from core.check_increment import CheckIncrementTimer
from core.settings import settings
from fastapi import BackgroundTasks, HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from redis.asyncio import Redis
from repositories.user_repo import UserRepo
from utils.security_generate import user_generate

from .email_service import send_password_reset_link, send_verification_email
from .sms_service import send_sms

reset_serializer = URLSafeTimedSerializer(settings.RESET_SECRET_KEY)
verify_serializer = URLSafeTimedSerializer(settings.VERIFY_EMAIL_SECRET_KEY)
redis = Redis.from_url(settings.CELERY_REDIS_URL, decode_responses=True)
resend_tracker: dict[str, dict] = {}


class UserVerification:
    def __init__(self, db):
        self.repo = UserRepo(db)
        self.check = CheckIncrementTimer()
    async def verify_reset_token(
        self, token: str, expiration: int = 3600
    ) -> str | None:
        try:
            email = reset_serializer.loads(
                token, salt=settings.RESET_PASSWORD_SALT, max_age=expiration
            )
            return email
        except (SignatureExpired, BadSignature):
            return None

    async def verify_verify_token(self, token: str, expiration: int = 3600) -> str | None:
        try:
            email = verify_serializer.loads(
                token, salt=settings.VERIFY_EMAIL_SALT, max_age=expiration
            )
            return email
        except (SignatureExpired, BadSignature):
            return None

    async def verify_otp(self, otp: str) -> str:
        async def handler():
            async for key in redis.scan_iter(match="otp:*"):
                stored = await redis.get(key)
                if stored == otp:
                    await redis.delete(key)
                    return key.split(":")[1]
            return None

        return await breaker.call(handler)

    async def resend_verification_email(self, email: str, background_tasks: BackgroundTasks):
        async def handler():
            user = await self.repo.get_by_email(email)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            if user.is_verified:
                return {"message": "Email already verified."}

            otp = await user_generate.generate_otp(email)
            token = user_generate.generate_verify_token(email)
            background_tasks.add_task(send_verification_email, email, otp, token)
            if hasattr(user, "phone_number") and user.phone_number:
                background_tasks.add_task(
                    send_sms.send_sms,
                    user.phone_number,
                    otp,
                    user.name,
                )
            return {"message": "Email Verification sent to your mailbox and sms"}

        return await breaker.call(handler)
    async def resend_password_reset_link(
        self, email: str, background_tasks: BackgroundTasks
    ):
        # self.check.check_and_increment_resend(email=email)

        async def handler():
            user = await self.repo.get_by_email(email)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            otp = await user_generate.generate_otp(email)
            token = await user_generate.generate_reset_token(email)
            background_tasks.add_task(send_password_reset_link, email, otp, token)
            if hasattr(user, "phone_number") and user.phone_number:
                background_tasks.add_task(
                    send_sms.send_sms,
                    user.phone_number,
                    otp,
                    user.name,
                )
            return {
                "message": "Password reset link via your email resent successfully."
            }

        return await breaker.call(handler)

    async def verify_email(self, otp: str | None = None, token: str | None = None):
        async def handler():
            if otp:
                email = await self.verify_otp(otp)
            elif token:
                email = await self.verify_reset_token(token)
            else:
                raise HTTPException(
                    status_code=400, detail="No verification data provided"
                )
            if not email:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or expired verification email",
                )
            user = await self.repo.get_by_email(email)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            user.is_verified = True
            await self.repo.save(user)
            return {"Message": "Email verified successfully"}

        return await breaker.call(handler)
    


