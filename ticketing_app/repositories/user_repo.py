from models.models import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class UserRepo:
    def __init__(self, db:AsyncSession):
        self.db = db

    async def get_name(self, name: str) -> User | None:
        result = self.db.execute(select(User).where(User.name == name))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, user: User):
        self.db.add(user)
        try:
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except:
            await self.db.rollback()
            raise
