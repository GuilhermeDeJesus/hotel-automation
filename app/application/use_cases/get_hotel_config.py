"""Get hotel configuration including policies and general info."""
from __future__ import annotations

from typing import Any, Optional

from app.domain.repositories.hotel_repository import HotelRepository


class GetHotelConfigUseCase:
    def __init__(self, hotel_repository: HotelRepository):
        self.hotel_repository = hotel_repository

    def execute(self, hotel_id: str) -> Optional[dict[str, Any]]:
        hotel = self.hotel_repository.get_active_hotel(hotel_id)
        if not hotel:
            return None
        return {
            "id": hotel.id,
            "name": hotel.name,
            "address": hotel.address,
            "contact_phone": hotel.contact_phone,
            "checkin_time": hotel.policies.checkin_time,
            "checkout_time": hotel.policies.checkout_time,
            "cancellation_policy": hotel.policies.cancellation_policy,
            "pet_policy": hotel.policies.pet_policy,
            "child_policy": hotel.policies.child_policy,
            "amenities": hotel.policies.amenities,
            "requires_payment_for_confirmation": getattr(
                hotel, "requires_payment_for_confirmation", False
            ),
            "allows_reservation_without_payment": getattr(
                hotel, "allows_reservation_without_payment", True
            ),
        }
