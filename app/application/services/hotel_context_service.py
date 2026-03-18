"""
Hotel Context Service - provides hotel information for AI conversations.

Reads hotel details from the repository and formats them into a
context string that can be injected into the AI system prompt.
"""
from typing import Dict, Optional

from app.domain.repositories.hotel_repository import HotelRepository


class HotelContextService:
    """Formats hotel context for AI conversations."""

    def __init__(self, hotel_repository: HotelRepository, context_data: Dict[str, str] | None = None):
        self.hotel_repository = hotel_repository
        self.context_data = context_data or {}

    def get_context(self, hotel_id: Optional[str] = None) -> str:
        """
        Build a context string with hotel details.

        Uses repository data when present. If nothing is configured,
        returns an empty string so the AI does not hallucinate facts.
        """
        data = self._load_context_data(hotel_id=hotel_id)
        if not any(value for value in data.values()):
            return ""

        lines = ["CONTEXTO DO HOTEL:"]
        self._append_if(lines, "Nome", data.get("name"))
        self._append_if(lines, "Endereco", data.get("address"))
        self._append_if(lines, "Check-in", data.get("checkin_time"))
        self._append_if(lines, "Check-out", data.get("checkout_time"))
        self._append_if(lines, "Politicas", data.get("policies"))
        self._append_if(lines, "Servicos", data.get("amenities"))
        self._append_if(lines, "Contato", data.get("contact"))
        lines.append("")
        return "\n".join(lines)

    def _load_context_data(self, hotel_id: Optional[str] = None) -> Dict[str, str]:
        # Allow explicit overrides (useful for tests)
        if self.context_data:
            return self.context_data

        hotel = self.hotel_repository.get_active_hotel(hotel_id)
        if not hotel:
            return {}

        return {
            "name": hotel.name,
            "address": hotel.address,
            "checkin_time": hotel.policies.checkin_time,
            "checkout_time": hotel.policies.checkout_time,
            "policies": (
                f"Cancelamento: {hotel.policies.cancellation_policy} | "
                f"Pets: {hotel.policies.pet_policy} | "
                f"Criancas: {hotel.policies.child_policy}"
            ),
            "amenities": hotel.policies.amenities,
            "contact": hotel.contact_phone,
        }

    @staticmethod
    def _append_if(lines: list[str], label: str, value: str | None) -> None:
        if value:
            lines.append(f"- {label}: {value}")
