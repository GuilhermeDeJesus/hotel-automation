"""
Cancel Reservation Response DTO - carries cancellation results.
"""


class CancelReservationResponseDTO:
    """Data Transfer Object for reservation cancellation responses."""

    def __init__(
        self,
        message: str,
        success: bool = True,
        can_cancel: bool = False,
        summary: str | None = None,
        status: str | None = None,
    ):
        self.message = message
        self.success = success
        self.can_cancel = can_cancel
        self.summary = summary
        self.status = status
