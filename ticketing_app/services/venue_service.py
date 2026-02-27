
import uuid
from datetime import datetime, timezone
from pathlib import Path

from core.cache import cache
from core.geoapify import geocode_address
from core.json_response import SerializeResponse
from core.mapper import ORMMapper
from core.paginate import PaginatePage
from core.utils import publish_event
from fastapi import HTTPException
from geoalchemy2.shape import from_shape
from models.models import Venue
from repositories.venue_repo import VenueRepo
from schemas.schema import VenueOut
from worker.celery_app import app as task_app

UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class VenueService:
    def __init__(self, db):
        self.repo = VenueRepo(db)
        self.paginate: PaginatePage = PaginatePage()
        self.mapper: ORMMapper = ORMMapper()
        self.serialize_json = SerializeResponse()

    async def check_venue_exists(
        self, venue_id: int, current_user,
    ) -> Venue:
        venue = await self.repo.get_by_id(venue_id)

        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        if venue.created_by != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Not Allowed",
            )

        return venue

    async def check_venue_exists_and_available(
        self, venue_id: int, current_user, is_available: bool = False
    ) -> Venue:
        venue = await self.repo.get_by_id(venue_id)

        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        if venue.created_by != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Not Allowed",
            )
        if venue.is_available == is_available:
            raise HTTPException(400, "This venue is not available")

        return venue

    async def list_venues(self, per_page: int = 20, page: int = 1):

        cache_key = f"venues:all:{page}:{per_page}"
        cached = await cache.async_get_json(cache_key)
        if cached:
            return self.mapper.many(items=cached, schema=VenueOut)

        venues = await self.repo.get_all(page=page, per_page=per_page)
        venue_dicts = self.mapper.many(items=venues, schema=VenueOut)
        if not venue_dicts:
            return []
        paginate = self.paginate.paginate(venue_dicts, page, per_page)

        await cache.async_set_json(cache_key, self.serialize_json.get_list_json_dumps(paginate), ttl=300)
        return paginate

    async def get_venue(self, venue_id: int):

        cache_key = f"venue:{venue_id}"
        cached = await cache.async_get_json(cache_key)
        if cached:
            return self.mapper.one(item=cached, schema=VenueOut)

        venues = await self.repo.get_venue(venue_id=venue_id)
        venue_dicts = self.mapper.one(item=venues, schema=VenueOut)
        if not venue_dicts:
            raise HTTPException(404, "Not Found")

        await cache.async_set_json(cache_key, self.serialize_json.get_single_json_dumps(venue_dicts), ttl=300)
        return venue_dicts

    async def create_venue(
        self, name: str, address: str, capacity: int, current_user, state_id: int,  files: list,
    ):
        # suffix = Path(file.filename).suffix
        # unique_name = f"{uuid.uuid4()}{suffix}"
        # file_path = UPLOAD_DIR / unique_name

        # with file_path.open("wb") as buffer:
        #     buffer.write(await file.read())

        saved_paths = []

        for file in files:
            unique_name = f"{uuid.uuid4()}{Path(file.filename).suffix}"
            file_path = UPLOAD_DIR / unique_name

            with file_path.open("wb") as buffer:
                buffer.write(await file.read())

            saved_paths.append(str(file_path))

        if await self.repo.get_by_name(name=name):
            raise HTTPException(
                status_code=400, detail="Name already taken")
        if await self.repo.get_by_address(address=address):
            raise HTTPException(
                status_code=400, detail="Address already taken")
        point = await geocode_address(address)
        geom = from_shape(point, srid=4326)

        if await self.repo.get_location(geom):
            raise HTTPException(
                status_code=400, detail="A venue already exists at this location.")

        venue = await self.repo.create(
            name=name,
            address=address,
            capacity=capacity,
            created_by=current_user.id,
            geom=geom,
            state_id=state_id

        )
        task_app.send_task("sync_upload_venue_images", args=[
            str(venue.created_by),
            str(venue.id),
            saved_paths,
        ],
        )

        await cache.delete_cache_keys_async("venues:all", f"venue:{venue.id}")
        await publish_event(
            "venue.created",
            {
                "venue_id": venue["id"],
                "name": venue["name"],
                "address": venue["address"],
                "capacity": venue["capacity"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        return {
            "id": venue.id,
            "name": venue.name,
            "address": venue.address,
            "capacity": venue.capacity,
            "location": {"latitude": point.y, "longitude": point.x},
        }

    async def update_venue(self, venue_id: int, data, current_user):

        user_id = current_user.id

        await self.check_venue_exists_and_available(
            venue_id=venue_id, current_user=current_user
        )
        updated_data = data.model_dump(exclude_unset=True)
        if not updated_data:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update.",
            )
        state_id = updated_data.get("state_id")

        updated_data["updated_at"] = datetime.utcnow()

        updated = await self.repo.update(
            user_id=user_id,
            venue_id=venue_id,
            **updated_data,
        )

        if not updated:
            raise HTTPException(
                status_code=404, detail="Venue not found or not modified"
            )
        prop = await self.repo.get_venue_with_relations(updated.id)

        await publish_event(
            "venue.updated",
            {
                "venue_id": str(updated.id),
                "name": updated.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        await cache.delete_cache_keys_async("venues:all", f"venue:{venue_id}")

        return self.mapper.one(prop, VenueOut)

    async def mark_venue_available(self, venue_id: int, current_user):
        user_id = current_user.id
        await self.check_venue_exists(
            venue_id=venue_id, current_user=current_user
        )
        marked = await self.repo.mark_as_available(user_id=user_id, venue_id=venue_id, is_available=True)
        if not marked:
            raise HTTPException(
                detail="Not Marked", status_code=400
            )
        await cache.delete_cache_keys_async("venues:all", f"venue:{venue_id}")
        return {"message": "Successfully marked as avaliable", "venue_id": venue_id}

    async def mark_venue_unavailable(self, venue_id: int, current_user):
        user_id = current_user.id
        await self.check_venue_exists(
            venue_id=venue_id, current_user=current_user
        )
        marked = await self.repo.mark_as_available(user_id=user_id, venue_id=venue_id, is_available=False)
        if not marked:
            raise HTTPException(
                detail="Not Marked", status_code=400
            )
        await cache.delete_cache_keys_async("venues:all", f"venue:{venue_id}")
        return {"message": "Successfully marked as unavaliable", "venue_id": venue_id}

    async def mark_venue_verified(self, venue_id: int, current_user):
        user_id = current_user.id
        await self.check_venue_exists(
            venue_id=venue_id, current_user=current_user
        )
        marked = await self.repo.mark_as_verified(user_id=user_id, venue_id=venue_id, is_available=False)
        if not marked:
            raise HTTPException(
                detail="Not Verified", status_code=400
            )
        await cache.delete_cache_keys_async("venues:all", f"venue:{venue_id}")
        return {"message": "Successfully verified", "venue_id": venue_id}

    async def delete(self, venue_id: int, current_user):
        await self.check_venue_exists(
            venue_id=venue_id, current_user=current_user
        )
        deleted = await self.repo.delete(venue_id=venue_id)
        await cache.delete_cache_keys_async("venues:all", f"venue:{venue_id}")
        return {
            "message": "Deleted",
            "id": str(deleted.id)
        }
