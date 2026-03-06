from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from app.domain.entities.reservation.reservation import Reservation


# Interface
# Define como o domínio (Reservation) quer acessar os dados, sem salvar como os dados são realmente armazenados
# Ela funciona como uma ponte entre a camade de domínio e a camada de infraestrutura.

class ReservationRepository(ABC):
    @abstractmethod
    def save(self, reservation: Reservation) -> None:
        """Persist a reservation or update existing one."""
        pass

    @abstractmethod
    def find_by_id(self, reservation_id: str) -> Optional[Reservation]:
        """Return a reservation by ID, or None."""
        pass

    @abstractmethod
    def find_by_phone_number(self, phone_number: str) -> Optional[Reservation]:
        """Return a reservation matching the given phone number, or None."""
        pass

    @abstractmethod
    def find_confirmed_past_checkin_date(self, reference_date: date) -> List[Reservation]:
        """
        Return reservations with status=CONFIRMED and check_in_date < reference_date.

        Used by no-show job to mark reservations where guest did not show up.
        """
        pass

    @abstractmethod
    def list_reservations(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        status: Optional[str] = None,
        room_number: Optional[str] = None,
        limit: int = 100,
    ) -> List[Reservation]:
        """
        List reservations with optional filters.
        Dates filter by check_in_date range.
        """
        pass

    @abstractmethod
    def count_by_status(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict[str, int]:
        """
        Count reservations by status. Dates filter by check_in_date range.
        Excludes CANCELLED and NO_SHOW.
        Returns dict like {"PENDING": n, "CONFIRMED": n, "CHECKED_IN": n, "CHECKED_OUT": n}.
        """
        pass
