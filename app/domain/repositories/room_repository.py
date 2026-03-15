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
    def list_all(self, hotel_id: str) -> List[Room]:
        """
        List all active rooms for a hotel.
        Args:
            hotel_id: The hotel identifier
        """
        pass

    @abstractmethod
    def get_by_number(self, hotel_id: str, room_number: str) -> Optional[Room]:
        """
        Retrieve room by number for a hotel.
        Args:
            hotel_id: The hotel identifier
            room_number: Room number
        """
        pass

    @abstractmethod
    def find_available(
        self, hotel_id: str, check_in: date, check_out: date, exclude_room: Optional[str] = None
    ) -> List[Room]:
        """
        Find available rooms for a date range in a hotel.
        Args:
            hotel_id: The hotel identifier
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
        hotel_id: str,
        room_number: str,
        check_in: date,
        check_out: date,
        exclude_reservation_id: Optional[str] = None,
    ) -> bool:
        """
        Check if specific room is available for dates in a hotel.
        Args:
            hotel_id: The hotel identifier
            room_number: Room to check
            check_in: Check-in date
            check_out: Check-out date
            exclude_reservation_id: If provided, ignore this reservation (e.g. when changing dates)
        """
        pass

    @abstractmethod
    def save(self, room: Room) -> Room:
        """Create or update a room. Returns the saved room with id set on create."""
        pass

    @abstractmethod
    def deactivate(self, room_number: str) -> bool:
        """Soft delete a room by setting is_active=False. Returns True if found and deactivated."""
        pass
