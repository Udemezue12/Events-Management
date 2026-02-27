from fastapi import Depends,  HTTPException, Request

from core.get_db import get_db_async
from models.models import User
from core.validators import jwt_protect, passkey_jwt_protect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession



async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db_async),
    
):
    
    user = await jwt_protect(request=request, db=db)

    if user:
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account suspended")
        return user


   
    raise HTTPException(
        status_code=401,
        detail="Not Authenticated",
    )


async def passkey_get_current_user(
    user_id: str = Depends(passkey_jwt_protect),
    db: AsyncSession = Depends(get_db_async),
) -> User:
    user = await db.execute(select(User).where(User.id == user_id))
    user_result = user.scalars().first()
    if not user_result:
        raise HTTPException(status_code=404, detail="User not found")
    return user_result
