import logging
from typing import List



from core.get_db import get_db_async
from core.safe_handler import safe_handler
from core.throttling import rate_limit
from core.validators import validate_csrf_dependency
from fastapi import APIRouter, Depends, File, UploadFile
from core.require_permissions import require_organizer_and_admin_user,  require_admin_user
from fastapi_utils.cbv import cbv
from models.models import User
from schemas.schema import VenueCreate, VenueOut, VenueUpdate
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
        files: list[UploadFile] = File(...),
        current_user: User = Depends(require_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency)
    ):
        
                
            return await VenueService(db).create_venue(
                name=payload.name,
                address=payload.address,
                capacity=payload.capacity,
                current_user=current_user,
                state_id=payload.state_id,
                files=files
            )
    @router.patch("/update/{venue_id}", dependencies=[rate_limit], response_model=VenueOut)
    @safe_handler
    async def update_venue(
        self,
        venue_id:int,
        data: VenueUpdate,
        current_user: User = Depends(require_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency)
    ):
        
                
            return await VenueService(db).update_venue(
                venue_id=venue_id, data=data, current_user=current_user
            )

       

    @router.get("/venues", dependencies=[rate_limit], response_model=List[VenueOut])
    @safe_handler
    async def list_venues(
        self, 
        per_page: int = 20, 
        page: int = 1,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency)
    ):
        
            return await VenueService(db).list_venues(page=page, per_page=per_page)
    @router.get("/{venue_id}/venue", dependencies=[rate_limit], response_model=VenueOut)
    @safe_handler
    async def get_venue(
        self, 
        venue_id:int,
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency)
    ):
        
            return await VenueService(db).get_venue(venue_id)
    @router.post("/{venue_id}/mark/verified", dependencies=[rate_limit])
    @safe_handler
    async def mark_as_verified(
        self, 
        venue_id:int,
        current_user: User = Depends(require_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency)
    ):
        
            return await VenueService(db).mark_venue_verified(venue_id=venue_id, current_user=current_user)
    @router.post("/{venue_id}/mark/unavailable", dependencies=[rate_limit])
    @safe_handler
    async def mark_as_unavailable(
        self, 
        venue_id:int,
        current_user: User = Depends(require_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency)
    ):
        
            return await VenueService(db).mark_venue_unavailable(venue_id=venue_id, current_user=current_user)
    @router.post("/{venue_id}/mark/available", dependencies=[rate_limit])
    @safe_handler
    async def mark_as_unvailable(
        self, 
        venue_id:int,
        current_user: User = Depends(require_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency)
    ):
        
            return await VenueService(db).mark_venue_available(venue_id=venue_id, current_user=current_user)
    @router.delete("/{venue_id}/delete", dependencies=[rate_limit])
    @safe_handler
    async def delete_venue(
        self, 
        venue_id:int,
        current_user: User = Depends(require_organizer_and_admin_user),
        db: AsyncSession = Depends(get_db_async),
        _: None = Depends(validate_csrf_dependency)
    ):
        
            return await VenueService(db).delete(venue_id=venue_id, current_user=current_user)

    
            

      
