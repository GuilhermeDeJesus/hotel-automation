from abc import ABC, abstractmethod

class ConversationCacheRepository(ABC):
    @abstractmethod
    def get(self, hotel_id: str, phone: str) -> None:
        """Retrieve cached conversation data for a hotel and phone."""
        pass

    @abstractmethod
    def set(self, hotel_id: str, phone: str, data: str) -> None:
        """Set cached conversation data for a hotel and phone."""
        pass