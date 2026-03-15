"""Create a new room."""
from __future__ import annotations

from app.domain.entities.room.room import Room
from app.domain.repositories.room_repository import RoomRepository


class CreateRoomUseCase:
    def __init__(self, room_repository: RoomRepository):
        self.room_repository = room_repository

    def execute(
        self,
        number: str,
        room_type: str,
        daily_rate: float,
        max_guests: int,
    ) -> dict:
        existing = self.room_repository.get_by_number(number)
        if existing:
            return {"success": False, "error": f"Quarto {number} já existe."}

        room = Room(
            number=number.strip(),
            room_type=room_type,
            daily_rate=daily_rate,
            max_guests=max_guests,
            status="AVAILABLE",
        )
        saved = self.room_repository.save(room)
        return {
            "success": True,
            "room": {
                "id": saved.id or "",
                "number": saved.number,
                "room_type": saved.room_type,
                "daily_rate": saved.daily_rate,
                "max_guests": saved.max_guests,
                "status": saved.status,
            },
        }
