import asyncio
from datetime import datetime
from typing import List

from core.breaker import breaker
from core.cache import cache
from core.utils import publish_event
from models.models import User
from repositories.review_repo import ReviewRepo


class ReviewService:
    def __init__(self, db):
        self.repo = ReviewRepo(db)

    async def add_review(
        self, user: User, event_id: int, rating: int, comment: str | None = None
    ):
        async def handler():
            event = await self.repo.get_event_by_id(event_id)
            if not event:
                raise ValueError("Event not found.")
            if event.created_by == user.id:
                raise ValueError("You cannot review your own event.")
            existing = await self.repo.get_user_review_for_event(user.id, event_id)
            if existing:
                raise ValueError("You have already reviewed this event.")
            review = await self.repo.create_review(user.id, event_id, rating, comment)

            await asyncio.create_task(
                publish_event(
                    "review.added",
                    {
                        "review_id": review.id,
                        "event_id": event_id,
                        "user_id": user.id,
                        "rating": rating,
                        "comment": comment,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                ),
            )
            await cache.delete(f"event:{event_id}:reviews")
            await cache.delete(f"user:{user.id}:reviews")
            return review

        return await breaker.call(handler)

    async def get_event_reviews(self, event_id: int) -> List[dict]:
        async def handler():
            cache_key = f"event:{event_id}:reviews"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached

            reviews = await self.repo.get_reviews_by_event(event_id)
            if not reviews:
                return []
            await cache.set_json(cache_key, reviews, ttl=300)

            await asyncio.create_task(
                publish_event(
                    "event.reviews.fetched",
                    {
                        "event_id": event_id,
                        "reviews_count": len(reviews),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                ),
            )
            return reviews

        return await breaker.call(handler)

    async def get_user_reviews(self, user_id: int) -> List[dict]:
        async def handler():
            cache_key = f"user:{user_id}:reviews"
            cached = await cache.get_json(cache_key)
            if cached:
                return cached

            reviews = await self.repo.get_reviews_by_user(user_id)
            if not reviews:
                return []
            await cache.set_json(cache_key, reviews, ttl=300)

            await asyncio.create_task(
                publish_event(
                    "user.reviews.fetched",
                    {
                        "user_id": user_id,
                        "reviews_count": len(reviews),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                ),
            )
            return reviews

        return await breaker.call(handler)
