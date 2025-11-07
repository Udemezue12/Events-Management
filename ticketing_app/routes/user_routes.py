import logging

from core.breaker import breaker
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from repositories.user_repo import UserRepo
from schemas.schema import UserCreate, UserOut
from services.user_service import UserService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Users"])


@cbv(router)
class UserRoutes:
    @router.post("/users/create", response_model=UserOut, dependencies=[rate_limit])
    @safe_handler
    async def create_user(
        self, data: UserCreate, db: AsyncSession = Depends(get_db_async)
    ):
        async def handler():
            user = await UserService(db).create_user(data)
            return user

        return await breaker.call(handler)
