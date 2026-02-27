import jwt
from fastapi import HTTPException, Request, status, Depends
from core.settings import settings
from models.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from core.get_db import get_db_async
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


async def validate_csrf(request: Request):
    try:
        session_token = request.session.get("csrf_token")
        cookie_token = request.cookies.get("csrf_token")

        header_token = request.headers.get("x-csrf-token")
        body_token = None

        # Try to read JSON body safely
        if request.method in ["POST", "PUT", "DELETE"]:
            try:
                body = await request.json()
                body_token = body.get("csrf_token")
            except Exception:
                body_token = None

        token = header_token or body_token

        print("SESSION:", session_token)
        print("COOKIE :", cookie_token)
        print("HEADER :", header_token)
        print("BODY   :", body_token)

        if not token:
            return

        # ✅ If token was sent → validate it
        if not session_token or not cookie_token:
            raise HTTPException(403, "Missing CSRF session or cookie")

        if not (session_token == cookie_token == token):
            raise HTTPException(
                status_code=403,
                detail="CSRF token mismatch",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"CSRF validation failed: {str(e)}",
        )



async def validate_csrf_dependency(
    request: Request,
):
    try:
        if any(
            path in str(request.url) for path in ["/docs", "/openapi.json", "/redoc"]
        ):
            return
        await validate_csrf(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def jwt_protect(request: Request, db: AsyncSession):
    token = request.cookies.get("access_token")
    if not token:
        return None

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if not user_id:
            return None

        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    except jwt.ExpiredSignatureError:
        return None

    except jwt.InvalidTokenError:
        return None


async def passkey_jwt_protect(request: Request) -> int:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token missing user ID")
        return int(user_id)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")