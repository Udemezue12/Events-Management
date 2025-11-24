import asyncio
from datetime import datetime
from typing import List

from core.breaker import breaker
from core.cache import cache
from core.utils import publish_event
from fastapi import HTTPException
from repositories.venue_repo import VenueRepo


class VenueService:
    def __init__(self, db):
        self.repo = VenueRepo(db)

    async def list_venues(self) -> List[dict]:
        async def handler():
            cache_key = "venues:list"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached

            venues = await self.repo.get_all()
            venue_dicts = [v.as_dict() for v in venues]

            await cache.set_json(cache_key, venue_dicts, ttl=300)
            return venue_dicts

        return await breaker.call(handler)

    async def create_venue(
        self, name: str, address: str, capacity: int, created_by=None
    ):
        async def handler():
            if await self.repo.get_by_name(name=name):
                raise HTTPException(status_code=400, detail="Name already taken")

            # if location:
            #     geopy_data = await geocode_location(location)
            #     if geopy_data:
            #         geo_point = geopy_data["point"]

            venue = await self.repo.create(
                name=name,
                address=address,
                capacity=capacity,
                created_by=created_by,
            )

            await asyncio.create_task(
                publish_event(
                    "venue.created",
                    {
                        "venue_id": venue["id"],
                        "name": venue["name"],
                        "address": venue["address"],
                        "capacity": venue["capacity"],
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                ),
            )
            await cache.delete("venues:list")
            return venue

        return await breaker.call(handler)
