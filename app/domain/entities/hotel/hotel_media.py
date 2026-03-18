from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class HotelMedia:
    id: str
    hotel_id: str
    scope: str  # "HOTEL" ou "ROOM"
    room_number: Optional[str]
    caption: Optional[str]
    sort_order: int
    mime_type: str
    filename: Optional[str]
    data: bytes
    created_at: datetime

