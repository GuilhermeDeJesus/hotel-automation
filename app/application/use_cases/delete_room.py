"""Soft delete a room (deactivate)."""
from __future__ import annotations

from app.domain.repositories.room_repository import RoomRepository


class DeleteRoomUseCase:
    def __init__(self, room_repository: RoomRepository):
        self.room_repository = room_repository

    def execute(self, room_number: str) -> dict:
        ok = self.room_repository.deactivate(room_number)
        if not ok:
            return {"success": False, "error": f"Quarto {room_number} não encontrado ou já desativado."}
        return {"success": True, "message": "Quarto desativado."}
