from app.domain.entities.hotel.policies import HotelPolicies


class Hotel:
    """Hotel aggregate root with policies and contact information."""

    def __init__(
        self,
        hotel_id: str,
        name: str,
        address: str,
        contact_phone: str,
        policies: HotelPolicies,
        is_active: bool = True,
    ):
        self.id = hotel_id
        self.name = name
        self.address = address
        self.contact_phone = contact_phone
        self.policies = policies
        self.is_active = is_active