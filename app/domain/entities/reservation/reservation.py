from app.domain.value_objects.phone_number import PhoneNumber
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain import exceptions

class Reservation:
    
    ## Atributos
    def __init__(self, reservation_id: str, guest_name: str, guest_phone: PhoneNumber, status: ReservationStatus):
        self.id = reservation_id
        self.guest_name = guest_name
        self.guest_phone = guest_phone
        self.status = status
    
    ## O que um hóspede pode fazer com uma reserva: 1 - Checkin
    def check_in(self):
        if self.status not in [ReservationStatus.CONFIRMED, ReservationStatus.PENDING]:
            raise exceptions.InvalidCheckInState("Só é possível fazer check-in em reservas confirmadas ou pendentes.")
        self.status = ReservationStatus.CHECKED_IN

    def to_dict(self):
        return {
            "id": self.id,
            "guest_name": str(self.guest_name),
            "guest_phone": str(self.guest_phone),
            "status": self.status.name
        }
        
"""
📌Reserva: Regras

    Só faz check-in se:
        status = CONFIRMADA
        data atual ≥ data início

    Só faz check-out se:
        já fez check-in

    Reserva cancelada ou finalizada:
        não pode mudar estado

    Reserva conhece:

        Cliente (por ID)
        Hotel (por ID)
"""