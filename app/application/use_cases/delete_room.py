"""Soft delete a room (deactivate). Multi-tenant seguro."""
from __future__ import annotations
from app.domain.repositories.room_repository import RoomRepository

class DeleteRoomUseCase:
    def __init__(self, room_repository: RoomRepository):
        self.room_repository = room_repository

    def execute(self, hotel_id: str, room_number: str) -> dict:
        ok = self.room_repository.deactivate(hotel_id, room_number)
        if not ok:
            return {"success": False, "error": f"Quarto {room_number} não encontrado ou já desativado."}
        return {"success": True, "message": "Quarto desativado."}


