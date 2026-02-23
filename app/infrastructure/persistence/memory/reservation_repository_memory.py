from typing import Optional
from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.repositories.reservation_repository import ReservationRepository
from app.domain.value_objects.phone_number import PhoneNumber

class ReservationRepositoryMemory(ReservationRepository):
    
    def __init__(self):
        self._reservations: dict[str, Reservation] = {}
        
    def find_by_phone_number(self, phone_number: str) -> Optional[Reservation]:
        for reservarion in self._reservations.values():
            if(str(reservarion.guest_phone) == phone_number):
                return reservarion
        return None
        
    def save(self, reservation: Reservation) -> None:
        self._reservations[reservation.id] = reservation
        
    def seed(self, reservation_id: str, phone: str):
        reservation = Reservation(
            reservation_id=reservation_id,
            guest_phone=PhoneNumber(phone),
            status= ReservationStatus.CREATED
        )
        self.save(reservation)