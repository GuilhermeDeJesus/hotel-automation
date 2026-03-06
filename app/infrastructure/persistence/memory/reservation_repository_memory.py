from datetime import date, datetime
from typing import List, Optional

from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.repositories.reservation_repository import ReservationRepository
from app.domain.value_objects.phone_number import PhoneNumber


class ReservationRepositoryMemory(ReservationRepository):
    def __init__(self):
        self._reservations: dict[str, Reservation] = {}

    def find_by_id(self, reservation_id: str) -> Optional[Reservation]:
        return self._reservations.get(reservation_id)

    def find_confirmed_past_checkin_date(self, reference_date: date) -> List[Reservation]:
        """Return CONFIRMED reservations with check_in_date < reference_date."""
        result = []
        for r in self._reservations.values():
            if r.status != ReservationStatus.CONFIRMED:
                continue
            if r.stay_period and r.stay_period.start < reference_date:
                result.append(r)
        return result

    def find_by_phone_number(self, phone_number: str) -> Optional[Reservation]:
        for reservarion in self._reservations.values():
            if(str(reservarion.guest_phone) == phone_number):
                return reservarion
        return None

    def list_reservations(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        status: Optional[str] = None,
        room_number: Optional[str] = None,
        limit: int = 100,
    ) -> List[Reservation]:
        result = []
        for r in self._reservations.values():
            if from_date is not None and r.stay_period and r.stay_period.start < from_date:
                continue
            if to_date is not None and r.stay_period and r.stay_period.start > to_date:
                continue
            if status is not None and r.status.name != status.upper():
                continue
            if room_number is not None and r.room_number != room_number:
                continue
            result.append(r)
        def _sort_key(x):
            start = x.stay_period.start if x.stay_period else date.min
            created = x.created_at if hasattr(x, "created_at") and x.created_at else datetime.min
            return (start, created)

        result.sort(key=_sort_key, reverse=True)
        return result[:limit]

    def count_by_status(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self._reservations.values():
            if r.status.name in ("CANCELLED", "NO_SHOW"):
                continue
            if from_date is not None and r.stay_period and r.stay_period.start < from_date:
                continue
            if to_date is not None and r.stay_period and r.stay_period.start > to_date:
                continue
            counts[r.status.name] = counts.get(r.status.name, 0) + 1
        return counts

    def save(self, reservation: Reservation) -> None:
        self._reservations[reservation.id] = reservation
        
    def seed(self, reservation_id: str, phone: str):
        reservation = Reservation(
            reservation_id=reservation_id,
            guest_phone=PhoneNumber(phone),
            status= ReservationStatus.CREATED
        )
        self.save(reservation)