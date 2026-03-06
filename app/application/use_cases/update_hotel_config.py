"""Update hotel payment configuration."""
from __future__ import annotations

from app.domain.repositories.hotel_repository import HotelRepository


class UpdateHotelConfigUseCase:
    def __init__(self, hotel_repository: HotelRepository):
        self.hotel_repository = hotel_repository

    def execute(
        self,
        requires_payment_for_confirmation: bool | None = None,
        allows_reservation_without_payment: bool | None = None,
    ) -> dict:
        hotel = self.hotel_repository.get_active_hotel()
        if not hotel:
            return {"success": False, "error": "Nenhum hotel ativo encontrado."}

        if requires_payment_for_confirmation is not None:
            hotel.requires_payment_for_confirmation = requires_payment_for_confirmation
        if allows_reservation_without_payment is not None:
            hotel.allows_reservation_without_payment = allows_reservation_without_payment

        self.hotel_repository.save(hotel)
        return {
            "success": True,
            "message": "Configuração atualizada.",
            "requires_payment_for_confirmation": hotel.requires_payment_for_confirmation,
            "allows_reservation_without_payment": hotel.allows_reservation_without_payment,
        }
