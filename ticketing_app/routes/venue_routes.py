import logging
from typing import List

from core.breaker import breaker
from core.get_current_user import get_current_user
from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from fastapi import APIRouter, Depends, HTTPException
from fastapi_utils.cbv import cbv
from models.models import User
from schemas.schema import VenueCreate, VenueOut
from services.venue_service import VenueService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Venue"])


@cbv(router)
class VenueRoutes:
    @router.post("/create/venues", dependencies=[rate_limit], response_model=VenueOut)
    @safe_handler
    async def create_venue(
        self,
        payload: VenueCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency)
    ):
        async def handler():
            return await VenueService(db).create_venue(
                name=payload.name,
                address=payload.address,
                capacity=payload.capacity,
                
                created_by=current_user.id,
            )

        return await breaker.call(handler)

    @router.get("/venues", dependencies=[rate_limit], response_model=List[VenueOut])
    @safe_handler
    async def list_venues(
        self,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency)
    ):
        async def handler():
            if current_user.role.name not in ["admin", "organizer"]:
                raise HTTPException(status_code=403, detail="Not Permitted")
            venues = await VenueService(db).list_venues()
            if not venues:
                raise HTTPException(status_code=404, detail="Not Found")
            return venues

        return await breaker.call(handler)
