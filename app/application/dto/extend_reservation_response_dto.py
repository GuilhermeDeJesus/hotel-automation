"""
Extend Reservation Response DTO - carries extension results.
"""
from datetime import date
from typing import Optional


class ExtendReservationResponseDTO:
    """Data Transfer Object for reservation extension responses."""

    def __init__(
        self,
        message: str,
        success: bool = True,
        can_extend: bool = False,
        current_checkout: Optional[date] = None,
        summary: Optional[str] = None,
        status: Optional[str] = None,
    ):
        self.message = message
        self.success = success
        self.can_extend = can_extend
        self.current_checkout = current_checkout
        self.summary = summary
        self.status = status
