"""Update an existing room."""
from __future__ import annotations

from app.domain.entities.room.room import Room
from app.domain.repositories.room_repository import RoomRepository


class UpdateRoomUseCase:
    def __init__(self, room_repository: RoomRepository):
        self.room_repository = room_repository

    def execute(
        self,
        room_number: str,
        room_type: str | None = None,
        daily_rate: float | None = None,
        max_guests: int | None = None,
        status: str | None = None,
    ) -> dict:
        existing = self.room_repository.get_by_number(room_number)
        if not existing:
            return {"success": False, "error": f"Quarto {room_number} não encontrado."}

        room = Room(
            number=room_number,
            room_type=room_type if room_type is not None else existing.room_type,
            daily_rate=daily_rate if daily_rate is not None else existing.daily_rate,
            max_guests=max_guests if max_guests is not None else existing.max_guests,
            status=status if status is not None else existing.status,
            id=existing.id,
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
