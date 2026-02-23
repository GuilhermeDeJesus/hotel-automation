"""
Check-in Response DTO - Data Transfer Object for layer communication.

IMPORTANT: This DTO is for internal communication between layers.
Do NOT add business logic or validation here - that belongs in the domain layer.
DTOs are just data containers for transferring information.
"""


class CheckinResponseDTO:
    """
    Data Transfer Object for check-in responses.
    
    Simply transfers result data from application layer back to interface layer.
    """
    
    def __init__(self, message: str, success: bool = True, error: str = None):
        """
        Initialize check-in response DTO.
        
        Args:
            message: Response message
            success: Whether check-in was successful
            error: Optional error message
        """
        self.message = message
        self.success = success
        self.error = error