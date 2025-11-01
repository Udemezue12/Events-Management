from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    name: str
    email: EmailStr
    password:str

class UserCreate(UserBase):
    pass

class UserOut(BaseModel):
    id: int
    name:str
    email:EmailStr

    class Config:
        orm_mode = True


class EventCreate(BaseModel):
    title: str
    description: str | None = None
    start_time: datetime
    end_time: datetime
    total_tickets: int
    venue_address: str
    venue_lat: float = Field(..., description="Latitude of event venue")
    venue_lon: float = Field(..., description="Longitude of event venue")

class EventOut(EventCreate):
    id: int
    tickets_sold: int

    class Config:
        orm_mode = True
class TicketCreate(BaseModel):
    user_id: int
    event_id: int

class TicketOut(BaseModel):
    id: int
    user_id: int
    event_id: int
    status: str
    created_at: datetime

    class Config:
        orm_mode = True
class TicketHistoryResponse(BaseModel):
    id: int
    status: str
    reserved_at: datetime
    event_title: str
    location: str

    class Config:
        orm_mode = True