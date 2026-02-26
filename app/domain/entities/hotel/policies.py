class CheckinPolicy:
    def __init__(self, allowed_hour: int):
        self.allowed_hour = allowed_hour

    def is_allowed(self, hour: int) -> bool:
        return hour >= self.allowed_hour


class HotelPolicies:
    """Represents hotel policies and rules used by the AI context."""

    def __init__(
        self,
        checkin_time: str,
        checkout_time: str,
        cancellation_policy: str,
        pet_policy: str,
        child_policy: str,
        amenities: str,
    ):
        self.checkin_time = checkin_time
        self.checkout_time = checkout_time
        self.cancellation_policy = cancellation_policy
        self.pet_policy = pet_policy
        self.child_policy = child_policy
        self.amenities = amenities