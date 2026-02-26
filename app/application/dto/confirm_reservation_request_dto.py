"""
Confirm Reservation Request DTO - Data Transfer Object for confirmation.
"""


class ConfirmReservationRequestDTO:
    """Data Transfer Object for reservation confirmation requests."""

    def __init__(self, phone: str):
        self.phone = phone
