from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.hotel.hotel import Hotel


class HotelRepository(ABC):
    @abstractmethod
    def get_active_hotel(self, hotel_id: str) -> Optional[Hotel]:
        """Return the active hotel record for a hotel_id or None."""
        pass

    @abstractmethod
    def save(self, hotel_id: str, hotel: Hotel) -> None:
        """Persist a hotel record (insert or update) for a hotel_id."""
        pass
