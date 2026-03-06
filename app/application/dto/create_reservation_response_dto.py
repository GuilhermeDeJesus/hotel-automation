"""
Create Reservation Response DTO - carries creation results.
"""


class CreateReservationResponseDTO:
    """Data Transfer Object for reservation creation responses."""

    def __init__(
        self,
        message: str,
        success: bool = True,
        reservation_id: str | None = None,
    ):
        self.message = message
        self.success = success
        self.reservation_id = reservation_id
