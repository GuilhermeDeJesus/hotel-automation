"""Update hotel configuration including policies and general info."""
from __future__ import annotations

from app.domain.entities.hotel.policies import HotelPolicies
from app.domain.repositories.hotel_repository import HotelRepository


class UpdateHotelConfigUseCase:
    def __init__(self, hotel_repository: HotelRepository):
        self.hotel_repository = hotel_repository

    def execute(
        self,
        name: str | None = None,
        address: str | None = None,
        contact_phone: str | None = None,
        checkin_time: str | None = None,
        checkout_time: str | None = None,
        cancellation_policy: str | None = None,
        pet_policy: str | None = None,
        child_policy: str | None = None,
        amenities: str | None = None,
        requires_payment_for_confirmation: bool | None = None,
        allows_reservation_without_payment: bool | None = None,
    ) -> dict:
        hotel = self.hotel_repository.get_active_hotel()
        if not hotel:
            return {"success": False, "error": "Nenhum hotel ativo encontrado."}

        if name is not None:
            hotel.name = name
        if address is not None:
            hotel.address = address
        if contact_phone is not None:
            hotel.contact_phone = contact_phone
        if requires_payment_for_confirmation is not None:
            hotel.requires_payment_for_confirmation = requires_payment_for_confirmation
        if allows_reservation_without_payment is not None:
            hotel.allows_reservation_without_payment = allows_reservation_without_payment

        if any(
            x is not None
            for x in (
                checkin_time,
                checkout_time,
                cancellation_policy,
                pet_policy,
                child_policy,
                amenities,
            )
        ):
            hotel.policies = HotelPolicies(
                checkin_time=checkin_time if checkin_time is not None else hotel.policies.checkin_time,
                checkout_time=checkout_time if checkout_time is not None else hotel.policies.checkout_time,
                cancellation_policy=(
                    cancellation_policy if cancellation_policy is not None else hotel.policies.cancellation_policy
                ),
                pet_policy=pet_policy if pet_policy is not None else hotel.policies.pet_policy,
                child_policy=child_policy if child_policy is not None else hotel.policies.child_policy,
                amenities=amenities if amenities is not None else hotel.policies.amenities,
            )

        self.hotel_repository.save(hotel)
        return {
            "success": True,
            "message": "Configuração atualizada.",
        }
