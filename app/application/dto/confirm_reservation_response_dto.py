"""
Confirm Reservation Response DTO - carries confirmation results.
"""


class ConfirmReservationResponseDTO:
    """Data Transfer Object for reservation confirmation responses."""

    def __init__(
        self,
        message: str,
        success: bool = True,
        can_confirm: bool = False,
        summary: str | None = None,
        status: str | None = None,
    ):
        self.message = message
        self.success = success
        self.can_confirm = can_confirm
        self.summary = summary
        self.status = status
