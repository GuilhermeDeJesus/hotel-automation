"""Room Order Repository - 6.5."""
from abc import ABC, abstractmethod


class RoomOrderRepository(ABC):
    @abstractmethod
    def save(self, hotel_id: str, order_id: str, reservation_id: str, items_json: str, total: float) -> None:
        pass
