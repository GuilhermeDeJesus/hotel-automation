"""
Room Repository Interface - contract for room data access.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import date

from app.domain.entities.room.room import Room


class RoomRepository(ABC):
    """Interface for room data access operations."""

    @abstractmethod
    def get_by_number(self, room_number: str) -> Optional[Room]:
        """Retrieve room by number."""
        pass

    @abstractmethod
    def find_available(
        self, check_in: date, check_out: date, exclude_room: Optional[str] = None
    ) -> List[Room]:
        """
        Find available rooms for a date range.
        
        Args:
            check_in: Check-in date
            check_out: Check-out date
            exclude_room: Room number to exclude from results
            
        Returns:
            List of available room entities
        """
        pass

    @abstractmethod
    def is_available(
        self,
        room_number: str,
        check_in: date,
        check_out: date,
        exclude_reservation_id: Optional[str] = None,
    ) -> bool:
        """
        Check if specific room is available for dates.

        Args:
            room_number: Room to check
            check_in: Check-in date
            check_out: Check-out date
            exclude_reservation_id: If provided, ignore this reservation (e.g. when changing dates)
        """
        pass
