import jwt
from core.settings import settings
from fastapi import HTTPException, Request, status


async def validate_csrf(request: Request):
    try:
        session_token = request.session.get("csrf_token")
        cookie_token = request.cookies.get("csrf_token")
        header_token = request.headers.get("x-csrf_token")

        if not (session_token and cookie_token):
            # if not (session_token and cookie_token and header_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Missing CSRF token"
            )

        # Compare header vs cookie
        # if header_token != cookie_token:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="CSRF token mismatch (header vs cookie)",
        #     )

        if session_token != cookie_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token: mismatch with session token.",
            )

        return True

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSRF validation failed: {str(e)}")


async def validate_csrf_dependency(request: Request):
    try:
        if any(
            path in str(request.url) for path in ["/docs", "/openapi.json", "/redoc"]
        ):
            return
        await validate_csrf(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def jwt_protect(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        print("TOKEN FROM COOKIE:", token)
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token missing user ID")
        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")

    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


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
