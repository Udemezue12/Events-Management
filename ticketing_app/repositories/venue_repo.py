# from core.open_map import geocode_address
from core.geoapify import geocode_address
from fastapi import HTTPException
from geoalchemy2.shape import from_shape
from models.models import Venue
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError


class VenueRepo:
    def __init__(self, db):
        self.db = db

    async def get_all(self):
        result = await self.db.execute(select(Venue))
        return result.scalars().all()

    async def get_by_name(self, name: str) -> Venue | None:
        result = await self.db.execute(select(Venue).where(Venue.name == name))
        return result.scalar_one_or_none()
    async def get_by_address(self, address: str) -> Venue | None:
        result = await self.db.execute(select(Venue).where(Venue.address == address))
        return result.scalar_one_or_none()

    async def get_by_location(self, location: str) -> Venue | None:
        result = await self.db.execute(select(Venue).where(Venue.location == location))
        return result.scalar_one_or_none()



    async def create(self, name: str, address: str, capacity: int, created_by: int):
        point = await geocode_address(address)
        geom = from_shape(point, srid=4326)
        existing = await self.db.execute(select(Venue).where(Venue.location == geom))
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="A venue already exists at this location.")
        venue = Venue(
            name=name,
            address=address,
            capacity=capacity,
            location=geom,
            created_by=created_by,
        )
        self.db.add(venue)
        try:
            await self.db.commit()
            await self.db.refresh(venue)
            return {
                "id": venue.id,
                "name": venue.name,
                "address": venue.address,
                "capacity": venue.capacity,
                "location": {"latitude": point.y, "longitude": point.x},
            }
        except SQLAlchemyError:
            await self.db.rollback()
            raise
