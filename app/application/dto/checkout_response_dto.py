"""
Checkout Response DTO - Data Transfer Object for layer communication.

IMPORTANT: This DTO is for internal communication between layers.
Do NOT add business logic or validation here - that belongs in the domain layer.
DTOs are just data containers for transferring information.
"""


class CheckoutResponseDTO:
    """
    Data Transfer Object for check-out responses.

    Simply transfers result data from application layer back to interface layer.
    """

    def __init__(
        self,
        message: str,
        success: bool = True,
        error: str | None = None,
    ):
        """
        Initialize check-out response DTO.

        Args:
            message: Response message
            success: Whether check-out was successful
            error: Optional error message
        """
        self.message = message
        self.success = success
        self.error = error
