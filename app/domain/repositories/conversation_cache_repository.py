from abc import ABC, abstractmethod
from typing import Any, Optional

class ConversationCacheRepository(ABC):
    @abstractmethod
    def get(self, hotel_id: str, phone: str) -> Optional[Any]:
        """Retrieve cached conversation data for a hotel and phone."""
        pass

    @abstractmethod
    def set(
        self,
        hotel_id: str,
        phone: str,
        data: Any,
        ttl_seconds: int = 3600,
    ) -> None:
        """Set cached conversation data for a hotel and phone."""
        pass