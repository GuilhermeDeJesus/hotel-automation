"""
Extend Reservation Request DTO - Data Transfer Object for extension requests.
"""
from datetime import date
from typing import Optional


class ExtendReservationRequestDTO:
    """Data Transfer Object for reservation extension requests."""

    def __init__(self, phone: str, new_checkout: Optional[date] = None):
        self.phone = phone
        self.new_checkout = new_checkout
