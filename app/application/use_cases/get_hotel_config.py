"""Get hotel payment configuration."""
from __future__ import annotations

from typing import Any, Optional

from app.domain.repositories.hotel_repository import HotelRepository


class GetHotelConfigUseCase:
    def __init__(self, hotel_repository: HotelRepository):
        self.hotel_repository = hotel_repository

    def execute(self) -> Optional[dict[str, Any]]:
        hotel = self.hotel_repository.get_active_hotel()
        if not hotel:
            return None
        return {
            "id": hotel.id,
            "name": hotel.name,
            "requires_payment_for_confirmation": getattr(
                hotel, "requires_payment_for_confirmation", False
            ),
            "allows_reservation_without_payment": getattr(
                hotel, "allows_reservation_without_payment", True
            ),
        }
