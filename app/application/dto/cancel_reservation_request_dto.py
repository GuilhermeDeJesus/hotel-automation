"""
Cancel Reservation Request DTO - Data Transfer Object for cancellation.
"""


class CancelReservationRequestDTO:
    """Data Transfer Object for reservation cancellation requests."""

    def __init__(self, phone: str):
        self.phone = phone
