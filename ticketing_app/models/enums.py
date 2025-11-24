import enum


class Role(enum.Enum):
    admin = "admin"
    organizer = "organizer"
    attendee = "attendee"

class TicketType(enum.Enum):
    regular = "regular"
    vip = "vip"
    early_bird = "early_bird"

class EventStatus(enum.Enum):
    upcoming = "upcoming"
    ongoing = "ongoing"
    completed = "completed"
    cancelled = "cancelled"

class PaymentStatus(enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"
