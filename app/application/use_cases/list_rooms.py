"""List all active rooms."""
from __future__ import annotations

from typing import Any, List

from app.domain.repositories.room_repository import RoomRepository


class ListRoomsUseCase:
    def __init__(self, room_repository: RoomRepository):
        self.room_repository = room_repository

    def execute(self) -> List[dict[str, Any]]:
        rooms = self.room_repository.list_all()
        return [
            {
                "id": r.id or "",
                "number": r.number,
                "room_type": r.room_type,
                "daily_rate": r.daily_rate,
                "max_guests": r.max_guests,
                "status": r.status,
            }
            for r in rooms
        ]
