"""
OTA Sync Service - 6.9 Integração com OTAs.

Interface para sincronização com Booking.com, Airbnb, etc.
Reservas vindas de OTA podem seguir o mesmo fluxo de WhatsApp.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class OTAReservationDTO:
    external_id: str
    ota_source: str  # "booking", "airbnb"
    guest_name: str
    guest_phone: str
    check_in: date
    check_out: date
    room_number: str
    total_amount: float


class OTASyncService(ABC):
    """Interface para sincronização com OTAs."""

    @abstractmethod
    def fetch_new_reservations(self, since: Optional[date] = None) -> List[OTAReservationDTO]:
        """Busca reservas novas da OTA."""
        pass

    @abstractmethod
    def sync_calendar(self, room_id: str, start: date, end: date) -> bool:
        """Sincroniza disponibilidade do quarto."""
        pass


class OTASyncStub(OTASyncService):
    """Stub - implementação vazia para evolução futura."""

    def fetch_new_reservations(self, since: Optional[date] = None) -> List[OTAReservationDTO]:
        return []

    def sync_calendar(self, room_id: str, start: date, end: date) -> bool:
        return True
