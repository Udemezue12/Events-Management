import logging
from typing import List

from core.breaker import breaker
from core.get_current_user import get_current_user
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from fastapi import APIRouter, Depends, HTTPException
from fastapi_utils.cbv import cbv
from models.models import User
from schemas.schema import ReviewCreate, ReviewOut
from services.review_service import ReviewService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Reviews"])


@cbv(router)
class ReviewRoutes:
    @router.post("/add/reviews", dependencies=[rate_limit], response_model=ReviewOut)
    @safe_handler
    async def add_review(
        self,
        payload: ReviewCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
    ):
        async def handler():
            return await ReviewService(db).add_review(
                current_user, payload.event_id, payload.rating, payload.comment
            )

        return await breaker.call(handler)

    @router.get(
        "/event/{event_id}/reviews",
        dependencies=[rate_limit],
        response_model=List[ReviewOut],
    )
    @safe_handler
    async def get_event_reviews(
        self, event_id: int, db: AsyncSession = Depends(get_db_async)
    ):
        async def handler():
            reviews = await ReviewService(db).get_event_reviews(event_id)
            if not reviews:
                raise HTTPException(status_code=404, detail="Not Found")
            return reviews

        return await breaker.call(handler)

    @router.get(
        "/user", dependencies=[rate_limit], response_model=List[ReviewOut]
    )
    @safe_handler
    async def get_user_reviews(
        self,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
    ):
        async def handler():
            return await ReviewService(db).get_user_reviews(current_user.id)

        return await breaker.call(handler)