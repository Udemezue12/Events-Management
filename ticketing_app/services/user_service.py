from datetime import datetime
from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse
from core.breaker import breaker
from core.utils import publish_event
from utils.security_verification import send_verification_email
from utils.security_generate import user_generate
from models.models import User
from passlib.context import CryptContext
from repositories.user_repo import UserRepo

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    def __init__(self, db):
        self.repository: UserRepo = UserRepo(db)

    async def create_user(self, payload, background_tasks: BackgroundTasks):
        async def handler():
            existing_user = await self.repository.get_by_email(payload.email)
            if existing_user:
                raise ValueError("Email already registered")

            existing_name = await self.repository.get_name(payload.name)
            if existing_name:
                raise ValueError("Name already taken")

            hashed_password = pwd_context.hash(payload.password)
            user = User(
                name=payload.name,
                email=payload.email,
                hashed_password=hashed_password,
            )

            await self.repository.create(user)

            await publish_event(
                "user.created",
                {
                    "user_id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "created_at": datetime.utcnow().isoformat(),
                },
            )

            
            otp = await user_generate.generate_otp(user.email)
            token = await user_generate.generate_verify_token(user.email)

            background_tasks.add_task(send_verification_email, user.email, otp, token)

            return JSONResponse({"message": "Created Successfully, wait for verification"}, status_code=201)

        return await breaker.call(handler)
