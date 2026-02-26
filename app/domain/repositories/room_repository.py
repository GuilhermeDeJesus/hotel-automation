"""
Room Repository Interface - contract for room data access.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import date


class RoomRepository(ABC):
    """Interface for room data access operations."""

    @abstractmethod
    def get_by_number(self, room_number: str) -> Optional[dict]:
        """Retrieve room by number."""
        pass

    @abstractmethod
    def find_available(
        self, check_in: date, check_out: date, exclude_room: Optional[str] = None
    ) -> List[dict]:
        """
        Find available rooms for a date range.
        
        Args:
            check_in: Check-in date
            check_out: Check-out date
            exclude_room: Room number to exclude from results
            
        Returns:
            List of available room dicts with number, type, rate
        """
        pass

    @abstractmethod
    def is_available(
        self, room_number: str, check_in: date, check_out: date
    ) -> bool:
        """Check if specific room is available for dates."""
        pass
