import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException
from geoalchemy2.shape import from_shape

from core.breaker import breaker
from core.cache import cache

from core.utils import publish_event
from core.geoapify import geocode_address
from core.paginate import PaginatePage
from core.redis_idempotency import RedisIdempotency
from models.shape import convert_location
from repositories.state_repo import StateRepo
from schemas.schema import VenueOut, StateSchema
from states_list.states import STATES


class StateService:
    LOCK_KEY = "states:sync:v12"

    def __init__(self, db):
        self.repo: StateRepo = StateRepo(db)
        self.paginate: PaginatePage = PaginatePage()

        self.idempotency = RedisIdempotency(namespace="states-service-startup")

    async def get_all_states_wit_venues(self, page: int = 1, per_page: int = 20) -> List[dict]:
        async def handler():
            cache_key = "states:venues:list"
            cached = await cache.async_get_json(cache_key)
            if cached:
                return cached
            states = await self.repo.get_all(page=page, per_page=per_page)

            state_dicts = [
                StateSchema(
                    id=s.id,
                    name=s.name,
                    location=convert_location(s.location),
                    venues=[
                        VenueOut(
                            id=v.id, name=v.name, location=convert_location(
                                v.location)
                        )
                        for v in s.venues
                    ],
                ).model_dump(mode="json")
                for s in states
            ]
            if not state_dicts:
                return []
            paginated_states = self.paginate.paginate(
                state_dicts, page, per_page)
            await cache.async_set_json(cache_key, paginated_states, ttl=300)
            return paginated_states

        return await breaker.call(handler)

    async def get_state_with_venue(
        self, state_name: str
    ):
        async def handler():
            cache_key = f"state:{state_name}"

            cached = await cache.async_get_json(cache_key)
            if cached:
                return cached

            state = await self.repo.get_one(name=state_name)
            if not state:
                raise HTTPException(status_code=404, detail="State not found")

            await cache.async_set_json(cache_key, state, ttl=300)
            return state

        return await breaker.call(handler)

    async def get_all_states_with_venues(self, page: int = 1, per_page: int = 20):
        async def handler():
            cache_key = "states:with_venues::{page}:{per_page}"

            cached = await cache.async_get_json(cache_key)
            if cached:
                return cached

            states = await self.repo.get_all_with_venues(page=page, per_page=per_page)
            paginated_states = self.paginate.paginate(states, page, per_page)
            await cache.async_set_json(cache_key, paginated_states, ttl=300)
            return paginated_states

        return await breaker.call(handler)

    async def get_all_states(self, page: int = 1, per_page: int = 20):

        cache_key = "state_name:single_state"
        cached = await cache.get_json(cache_key)
        if cached:
            return cached
        states = await self.repo.get_all_states(per_page=per_page, page=page)
        state_dicts = [s.as_dict() for s in states]
        paginated_states = self.paginate.paginate(
            state_dicts, page, per_page)
        await cache.async_set_json(cache_key, paginated_states, ttl=300)
        return paginated_states

    async def get_all_states_without_pagination(self):

        cache_key = "states::without:pagination"
        cached = await cache.async_get_json(cache_key)
        if cached:
            return cached
        states = await self.repo.get_all_states_without_pagination()
        state_dicts = [s.as_dict() for s in states]
        
        await cache.async_set_json(cache_key, states, ttl=300)
        return states

    async def create_state(
        self,
    ):
        # async def _sync():
        print("Starting state sync...")

        for item in STATES:
            raw_name = item["name"].strip()
            point = await geocode_address(raw_name)
            geom = from_shape(point, srid=4326)

            state, created = await self.repo.create_or_get(name=raw_name, geom=geom)
            await self.repo.db_commit()

            if created:
                await publish_event(
                    "state.created",
                    {
                        "state_id": str(state.id),
                        "name": state.name,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

        await cache.delete_cache_keys_async(
            "states:list",
            "states:with_lgas",
        )

        print("State sync completed")

        # await self.idempotency.run_once(
        #     key=self.LOCK_KEY,
        #     coro=_sync,
        #     ttl=120,
        # )

    async def update_state(
        self, current_user, state_id: uuid.UUID, new_name: str | None = None
    ):

        state = await self.repo.update_one(
            state_id=state_id,
            new_name=new_name,
        )
        state_name = state.name

        await publish_event(
            "state.updated",
            {
                "state_id": str(state.id),
                "name": str(state_name),
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            },
        ),

        await cache.delete_cache_keys_async(
            f"state:{state_name}",
            "state_name:single_state",
            "states:list",
            "states:with_venues",
            states: venues: list
        )
        return state.as_dict()

    async def delete_state(
        self,
        current_user,
        name: str,
    ):

        state = await self.repo.get_name(name)
        if not state:
            raise HTTPException(status_code=404, detail="State not found")

        deleted = await self.repo.delete_one(name)
        state_name = deleted.name

        await cache.delete_cache_keys_async(
            f"state:{state_name}",
            "state_name:single_state",
            "states:list",
            "states:with_lgas",
        )
        (
            await publish_event(
                "state.deleted",
                {
                    "state_id": deleted.id,
                    "name": deleted.name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            ),
        )

        return {"deleted": True, "id": state["id"], "name": state["name"]}
