"""
Check-in Request DTO - Data Transfer Object for layer communication.

IMPORTANT: This DTO is for internal communication between layers.
Do NOT add business logic or validation here - that belongs in Value Objects 
or Use Cases. DTOs are just data containers.

For HTTP validation, use app/interfaces/schemas.py instead.
"""


class CheckinRequestDTO:
    """
    Data Transfer Object for check-in requests.
    
    Simply transfers data from interface layer to application layer.
    Validation happens in the use-case or domain layer.
    """
    
    def __init__(self, phone: str, name: str = None, room: str = None):
        """
        Initialize check-in DTO.
        
        Args:
            phone: Guest phone number
            name: Optional guest name
            room: Optional room number
        """
        self.phone_number = phone
        self.name = name
        self.room = room