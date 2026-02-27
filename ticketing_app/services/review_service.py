import asyncio
from datetime import datetime
from typing import List

from core.breaker import breaker
from core.cache import cache
from core.utils import publish_event
from models.models import User
from repositories.review_repo import ReviewRepo

from repositories.event_repo import EventRepo

class ReviewService:
    def __init__(self, db):
        self.repo = ReviewRepo(db)
        self.event_repo = EventRepo(db)


    async def add_review(
        self, user, event_id: int, rating: int, comment: str | None = None
    ):
        
            event = await self.event_repo.get_event_by_id(event_id)
            if not event:
                raise ValueError("Event not found.")
            if event.created_by == user.id:
                raise ValueError("You cannot review your own event.")
            existing = await self.repo.get_user_review_for_event(user.id, event_id)
            if existing:
                raise ValueError("You have already reviewed this event.")
            review = await self.repo.create_review(user.id, event_id, rating, comment)

            await publish_event(
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
            
            await cache.delete_cache_keys_async(f"event:{event_id}:reviews",f"user:{user.id}:reviews")
           
            return review

        

    async def get_event_reviews(self, event_id: int) -> List[dict]:
        
            cache_key = f"event:{event_id}:reviews"
            cached = await cache.async_get_json(cache_key)
            if cached:
                return cached

            reviews = await self.repo.get_reviews_by_event(event_id)
            if not reviews:
                return []
            await cache.async_set_json(cache_key, reviews, ttl=300)

            await publish_event(
                    "event.reviews.fetched",
                    {
                        "event_id": event_id,
                        "reviews_count": len(reviews),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                ),
            
            return reviews

        

    async def get_user_reviews(self, user_id: int) -> List[dict]:
        
            cache_key = f"user:{user_id}:reviews"
            cached = await cache.async_get_json(cache_key)
            if cached:
                return cached

            reviews = await self.repo.get_reviews_by_user(user_id)
            if not reviews:
                return []
            await cache.async_set_json(cache_key, reviews, ttl=300)

            await publish_event(
                    "user.reviews.fetched",
                    {
                        "user_id": user_id,
                        "reviews_count": len(reviews),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                ),
            
            return reviews

        
