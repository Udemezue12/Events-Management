from models.models import Event, Review, User
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError


class ReviewRepo:
    def __init__(self, db):
        self.db = db

    async def create_review(
        self, user_id: int, event_id: int, rating: int, comment: str | None = None
    ):
        review = Review(
            user_id=user_id, event_id=event_id, rating=rating, comment=comment
        )
        self.db.add(review)
        try:
            await self.db.commit()
            await self.db.refresh(review)
            return review
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_reviews_by_event(self, event_id: int):
        stmt = (
            select(Review, Event, User)
            .join(Review.event)
            .join(Review.user)
            .where(Review.event_id == event_id)
        )
        result = await self.db.execute(stmt)

        return [review.as_dict(user, event) for review, event, user in result.all()]

    async def get_reviews_by_user(self, user_id: int):
        stmt = (
           select(Review, Event, User)
           .join(Review.event)
           .join(Review.user)
           .where(Review.user_id == user_id)
        )
        result = await self.db.execute(stmt)

        return [review.as_dict(user, event) for review, event, user in result.all()]
  
    async def get_user_review_for_event(self, user_id: int, event_id: int):
        return (
            await self.db.execute(
                select(Review).where(
                   Review.user_id == user_id,
                   Review.event_id == event_id
                )
            )
        ).scalar_one_or_none()