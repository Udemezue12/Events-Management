from datetime import datetime

from core.utils import publish_event
from models.models import User
from passlib.context import CryptContext
from repositories.user_repo import UserRepo

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    def __init__(self, repository: UserRepo):
        self.repository = repository

    async def create_user(self, db, payload):
        existing_user = await self.repository.get_user_email(db, payload.email)
        if existing_user:
            raise ValueError("Email already registered")

        existing_name = await self.repository.get_name(db, payload.name)
        if existing_name:
            raise ValueError("Name already taken")

        hashed_password = pwd_context.hash(payload.password)
        user = User(
            name=payload.name,
            email=payload.email,
            hashed_password=hashed_password,
        )

        user = await self.repository.create(db, user)

        await publish_event(
            "user.created",
            {
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "created_at": datetime.utcnow().isoformat(),
            },
        )

        return user
