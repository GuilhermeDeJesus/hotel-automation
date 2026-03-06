"""
Checkout Request DTO - Data Transfer Object for layer communication.

IMPORTANT: This DTO is for internal communication between layers.
Do NOT add business logic or validation here - that belongs in Value Objects
or Use Cases. DTOs are just data containers.
"""


class CheckoutRequestDTO:
    """
    Data Transfer Object for check-out requests.

    Simply transfers data from interface layer to application layer.
    Validation happens in the use-case or domain layer.
    """

    def __init__(self, phone: str):
        """
        Initialize check-out request DTO.

        Args:
            phone: Guest phone number
        """
        self.phone = phone
