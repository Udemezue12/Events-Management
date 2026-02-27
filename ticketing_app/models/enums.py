import enum


class Role(str,enum.Enum):
    ADMIN = "ADMIN"
    ORGANIZER = "ORGANIZER"
    ATTENDEE = "ATTENDEE"

class TicketType(str,enum.Enum):
    REGULAR = "REGULAR"
    VIP = "VIP"
    EARLY_BIRD = "EARLY_BIRD"

class TicketStatus(str,enum.Enum):
    PENDING = "PENDING"
    RESERVED="RESERVED"
    SOLD = "SOLD"
    CANCELLED = "CANCELLED"
    REFUNDED="REFUNDED"
    CHECKED_IN="CHECKED_IN"

class EventStatus(str,enum.Enum):
    UPCOMING = "UPCOMING"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"
class PDFStatus(str, enum.Enum):
    PENDING="PENDING"
    READY="READY"
    GENERATING="GENERATING"
    FAILED = "FAILED"
class PaymentStatus(str,enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED="REFUNDED"
    REFUND_PROCESSING = "REFUND_PROCESSING"
    VERIFICATION_PENDING="VERIFICATION_PENDING"
class PaymentMethod(str, enum.Enum):
    NONE_YET="NONE_YET"
    PAYSTACK = "PAYSTACK"
    FLUTTERWAVE="FLUTTERWAVE"
    MONNIFY = "MONNIFY"
