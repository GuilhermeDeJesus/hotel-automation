from dataclasses import dataclass


@dataclass(frozen=True)
class Room:
    """Domain entity/value for a hotel room used in reservation flows."""

    number: str
    room_type: str
    daily_rate: float
    max_guests: int
    status: str
