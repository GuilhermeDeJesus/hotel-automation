from dataclasses import dataclass
from typing import Optional


class Room:
    """Domain entity for a hotel room used in reservation flows."""

    def __init__(
        self,
        number: str,
        room_type: str,
        daily_rate: float,
        max_guests: int,
        status: str,
        hotel_id: str,
        id: Optional[str] = None
    ):
        self.number = number
        self.room_type = room_type
        self.daily_rate = daily_rate
        self.max_guests = max_guests
        self.status = status
        self.hotel_id = hotel_id
        self.id = id
