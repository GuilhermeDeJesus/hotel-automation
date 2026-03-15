"""Support Ticket Repository - 6.6."""
from abc import ABC, abstractmethod


class SupportTicketRepository(ABC):
    @abstractmethod
    def save(self, hotel_id: str, ticket_id: str, reservation_id: str, description: str, category: str) -> None:
        pass
