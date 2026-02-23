from abc import ABC, abstractmethod
from typing import Optional
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
    def find_by_phone_number(self, phone_number: str) -> Optional[Reservation]:
        """Return a reservation matching the given phone number, or None."""
        pass
