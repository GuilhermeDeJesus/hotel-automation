from abc import ABC, abstractmethod

class ConversationCacheRepository(ABC):
    @abstractmethod
    def get(self, phone: str) -> None:
        pass
    
    @abstractmethod
    def set(self, phone: str, data: str) -> None:
        pass