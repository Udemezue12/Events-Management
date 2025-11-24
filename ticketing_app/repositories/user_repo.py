from datetime import datetime

from models.models import BlacklistedToken, User
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError


class UserRepo:
    def __init__(self, db):
        self.db = db

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> User | None:
        result = await self.db.execute(select(User).where(User.name == name))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_phoneNumber(self, phone_number: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.phone_number == phone_number)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        if user.id is not None:
            raise ValueError(
                "create() called with existing user — use update() instead"
            )
        self.db.add(user)
        return await self._commit_and_refresh(user)

    async def update(self, user: User) -> User:
        if user.id is None:
            raise ValueError("update() called with no ID — use create() instead")

        self.db.add(user)
        return await self._commit_and_refresh(user)

    

    async def save(self, user: User) -> User:
        self.db.add(user)
        return await self._commit_and_refresh(user)

    async def _commit_and_refresh(self, user: User) -> User:
        try:
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def blacklist_token(self, token: str):
        self.db.add(BlacklistedToken(token=token))
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def is_token_blacklisted(self, token: str) -> bool:
        result = await self.db.execute(
            select(BlacklistedToken).where(BlacklistedToken.token == token)
        )
        return result.scalar_one_or_none() is not None

    async def delete_expired_blacklisted_tokens(self, cutoff:datetime):
        try:
            await self.db.execute(
                delete(BlacklistedToken).where(BlacklistedToken.blacklisted_on < cutoff)
            )
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise
