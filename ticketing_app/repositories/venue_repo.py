# from core.open_map import geocode_address

from typing import Optional

from fastapi import HTTPException
from models.models import Venue
from sqlalchemy import select, update, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from datetime import datetime, timedelta, timezone

class VenueRepo:
    def __init__(self, db):
        self.db = db
    def count_user_uploads_between(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
    ) -> Venue:
        if start.tzinfo is not None:
            start = start.replace(tzinfo=None)

        if end.tzinfo is not None:
            end = end.replace(tzinfo=None)
        stmt = (
            select(func.count(Venue.id))
            .where(Venue.created_by == user_id)
            .where(Venue.uploaded_at >= start)
            .where(Venue.uploaded_at < end)
        )
        result = self.db.execute(stmt)
        return result.scalar_one()

    async def get_all(self, page: int = 1, per_page: int = 20, is_available: bool = True, is_verified: bool = True) -> list[Venue]:
        offset = (page - 1) * per_page
        result = await self.db.execute(
            select(Venue).where(Venue.is_available ==
                                is_available, Venue.is_verified == is_verified)
            .options(selectinload(Venue.events), selectinload(Venue.state))
            .order_by(Venue.name.desc())
            .offset(offset)
            .limit(per_page)
        )
        return result.scalars().all()

    async def get_venue(self, venue_id: int, is_available: bool = True, is_verified: bool = True) -> Optional[Venue]:

        result = await self.db.execute(
            select(Venue)
            .where(Venue.id == venue_id, Venue.is_available == is_available, Venue.is_verified == is_verified)
            .options(selectinload(Venue.events), selectinload(Venue.state))
            .order_by(Venue.name.desc())

        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Venue | None:
        result = await self.db.execute(select(Venue).where(Venue.name == name))
        return result.scalar_one_or_none()
    def sync_get_by_hash(self, venue_id:int,image_hash:str) -> Venue | None:
        result = self.db.execute(select(Venue).where(Venue.id==venue_id,Venue.image_hash == image_hash))
        return result.scalar_one_or_none()

    async def get_by_id(self, venue_id: int) -> Optional[Venue]:
        result = await self.db.execute(select(Venue).where(Venue.id == venue_id))
        return result.scalar_one_or_none()

    async def get_by_address(self, address: str) -> Venue | None:
        result = await self.db.execute(select(Venue).where(Venue.address == address))
        return result.scalar_one_or_none()

    async def get_by_location(self, location: str) -> Venue | None:
        result = await self.db.execute(select(Venue).where(Venue.location == location))
        return result.scalar_one_or_none()

    async def create(self, name: str, address: str, capacity: int, created_by: int, geom, state_id: int) -> Venue:

        venue = Venue(
            name=name,
            address=address,
            capacity=capacity,
            location=geom,
            created_by=created_by,
            state_id=state_id
        )
        self.db.add(venue)
        try:
            await self.db.commit()
            await self.db.refresh(venue)
            return venue

        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_location(self, geom):
        existing = await self.db.execute(select(Venue).where(Venue.location == geom))
        return existing.scalars().first()

    async def get_venue_with_relations(self, venue_id: int) -> Optional[Venue]:
        result = await self.db.execute(
            select(Venue)
            .options(
                selectinload(Venue.state),
                selectinload(Venue.events),
            )
            .where(Venue.id == venue_id)
        )
        return result.scalars().first()

    async def update(self, user_id: int, venue_id: Optional[int] = None, name: Optional[str] = None, address: Optional[str] = None, capacity: Optional[int] = None, geom=None):
        if not venue_id:
            raise HTTPException(
                status_code=400, detail="Venue ID is required for update.")
        venue_obj = await self.get_by_id(venue_id=venue_id)
        if not venue_obj:
            raise HTTPException(status_code=404, detail="Venue not found.")
        if venue_obj.created_by != user_id:
            raise HTTPException(
                status_code=403, detail="You do not have permission to update this venue.")
        if name is not None:
            venue_obj.name = name
        if address is not None:
            venue_obj.address = address
        if capacity is not None:
            venue_obj.capacity = capacity
        if geom is not None:
            venue_obj.location = geom
        self.db.add(venue_obj)
        try:
            await self.db.commit()
            await self.db.refresh(venue_obj)
            return venue_obj
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def mark_as_available(
        self,
        user_id: int,
        venue_id: int,
        is_available: bool,
    ):
        stmt = (
            update(Venue)
            .where(
                Venue.id == venue_id,
                Venue.created_by == user_id,

            )
            .values(is_available=is_available, )
            .returning(Venue)
        )

        try:
            await self.db.execute(stmt)
            await self.db.commit()

        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def mark_as_verified(
        self,
        user_id: int,
        venue_id: int,
        is_verified: bool,
    ):
        stmt = (
            update(Venue)
            .where(
                Venue.id == venue_id,
                Venue.created_by == user_id,

            )
            .values(is_verified=is_verified, )
            .returning(Venue)
        )

        try:
            await self.db.execute(stmt)
            await self.db.commit()

        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def delete(self, venue_id: int) -> Venue:
        venue = await self.get_by_id(venue_id=venue_id)
        await self.db.delete(venue)

        try:
            await self.db.commit()
            return venue

        except SQLAlchemyError:
            await self.db.rollback()
            raise

    def sync_upload_venue_image(self, user_id: int, venue_id: int, image_hash: str, image_url: str, public_id: str):
        stmt = (
            update(Venue)
            .where(
                Venue.id == venue_id,
                Venue.created_by == user_id,

            )
            .values(image_hash=image_hash, image_url=image_url, public_id=public_id)
            .returning(Venue)
        )

        try:
            self.db.execute(stmt)
            self.db.commit()

        except SQLAlchemyError:
            self.db.rollback()
            raise
