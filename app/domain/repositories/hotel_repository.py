from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.hotel.hotel import Hotel


class HotelRepository(ABC):
    @abstractmethod
    def get_active_hotel(self) -> Optional[Hotel]:
        """Return the active hotel record or None."""
        pass

    @abstractmethod
    def save(self, hotel: Hotel) -> None:
        """Persist a hotel record (insert or update)."""
        pass
