from enum import Enum

class ReservationStatus(Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CRECKED_IN"
    CHECKED_OUT = "CHECKOUT_OUT"
    CANCELLED = "CANCELLED"