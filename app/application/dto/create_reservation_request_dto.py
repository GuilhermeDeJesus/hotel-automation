"""
Create Reservation Request DTO - Data Transfer Object for reservation creation.
"""
from datetime import date


class CreateReservationRequestDTO:
    """Data Transfer Object for creating a new reservation."""

    def __init__(
        self,
        phone: str,
        check_in: date,
        check_out: date,
        room_number: str,
        guest_name: str,
    ):
        self.phone = phone
        self.check_in = check_in
        self.check_out = check_out
        self.room_number = room_number
        self.guest_name = guest_name
