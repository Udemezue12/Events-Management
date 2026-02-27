import logging
from typing import List

from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from core.require_permissions import require_attendee_organizer_and_admin_user, require_attendee_user
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from models.models import User
from schemas.schema import ReviewCreate, ReviewOut
from services.review_service import ReviewService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Reviews"])


@cbv(router)
class ReviewRoutes:
    @router.post("/{event_id}/add/reviews", dependencies=[rate_limit], response_model=ReviewOut)
    @safe_handler
    async def add_review(
        self,
        event_id: int,
        payload: ReviewCreate,
        current_user: User = Depends(require_attendee_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):

        return await ReviewService(db).add_review(
            current_user, event_id, payload.rating, payload.comment
        )

    @router.get(
        "/event/{event_id}/reviews",
        dependencies=[rate_limit],
        response_model=List[ReviewOut],
    )
    @safe_handler
    async def get_event_reviews(
        self,
        event_id: int,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
        current_user: User = Depends(
            require_attendee_organizer_and_admin_user),
    ):

        return await ReviewService(db).get_event_reviews(event_id)

    @router.get("/user", dependencies=[rate_limit], response_model=List[ReviewOut])
    @safe_handler
    async def get_user_reviews(
        self,
        current_user: User = Depends(
            require_attendee_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency),
    ):

        return await ReviewService(db).get_user_reviews(current_user.id)
