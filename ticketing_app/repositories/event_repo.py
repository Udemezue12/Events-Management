from models.models import Event
from sqlalchemy import func, select, text



class EventRepo:
    def __init__(self, db):
        self.db = db

    async def create(self, payload):
        locations = await self.db.execute(
            text("""
                INSERT INTO events (
                    title, description, start_time, end_time,
                    total_tickets, tickets_sold, venue_address, venue_location
                )
                VALUES (
                    :title, :description, :start_time, :end_time,
                    :total_tickets, 0, :venue_address,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                )
            """),
            {
                "title": payload.title,
                "description": payload.description,
                "start_time": payload.start_time,
                "end_time": payload.end_time,
                "total_tickets": payload.total_tickets,
                "venue_address": payload.venue_address,
                "lat": payload.venue_lat,
                "lon": payload.venue_lon,
            },
        )
        try:
           await self.db.commit()
           await self.db.refresh(locations)
           return locations
        except:
           await self.db.rollback()
           raise

    async def get_all(self):
        result = await self.db.scalars(select(Event))
        return result.all()

    async def get_nearby(self, lat: float, lon: float, radius=10_000):
        query = select(Event).where(
            func.ST_DWithin(Event.venue_location, func.ST_MakePoint(lon, lat), radius)
        )
        result = await self.db.scalars(query)
        return result.all()
