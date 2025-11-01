from models.models import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class UserRepo:
    async def get_user_email(self, db: AsyncSession, email: str):
        user_email = select(User).where(User.email == email)
        return await db.scalar(user_email)

    async def get_name(self, db: AsyncSession, name: str):
        names = select(User).where(User.name == name)
        return await db.scalar(names)

    async def create(self, db: AsyncSession, user: User):
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
