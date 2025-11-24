from core.get_db import get_db_async
from fastapi import Depends, HTTPException
from models.models import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .validators import jwt_protect, passkey_jwt_protect


async def get_current_user(
    user_id: str = Depends(jwt_protect), db: AsyncSession = Depends(get_db_async)
):
    try:
        user_id = int(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user id in token")
    user = await db.execute(select(User).where(User.id == user_id))
    user_result = user.scalars().first()
    if not user_result:
        raise HTTPException(status_code=404, detail="User not found")
    return user_result


async def passkey_get_current_user(
    user_id: str = Depends(passkey_jwt_protect),
    db: AsyncSession = Depends(get_db_async),
) -> User:
    user = await db.execute(select(User).where(User.id == user_id))
    user_result = user.scalars().first()
    if not user_result:
        raise HTTPException(status_code=404, detail="User not found")
    return user_result
