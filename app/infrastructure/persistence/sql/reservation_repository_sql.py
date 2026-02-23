from typing import Optional

from app.domain.entities.reservation.reservation import Reservation
from app.domain.repositories.reservation_repository import ReservationRepository
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.value_objects.phone_number import PhoneNumber
from .models import ReservationModel

class ReservationRepositorySQL(ReservationRepository):
    def __init__(self, session):
        self.session = session
        
    def find_by_phone_number(self, phone_number: str) -> Optional[Reservation]:
        reservation_model: ReservationModel | None = (
            self.session
            .query(ReservationModel)
            .filter_by(guest_phone=phone_number)
            .first()
        )
        if reservation_model:
            status_enum = ReservationStatus[reservation_model.status]
            return Reservation(         
                reservation_id=str(reservation_model.id),
                guest_name=reservation_model.guest_name,
                guest_phone=PhoneNumber(reservation_model.guest_phone),
                status=status_enum,
            )
        return None

    def save(self, reservation: Reservation) -> None:
        """Insert or update a reservation based on id or phone.
        """
        existing: ReservationModel | None = None

        if reservation.id:
            try:
                existing = self.session.query(ReservationModel).get(int(reservation.id))
            except Exception:
                existing = None

        if existing is None:
            existing = (
                self.session
                .query(ReservationModel)
                .filter_by(guest_phone=str(reservation.guest_phone))
                .first()
            )

        if existing:
            existing.guest_phone = str(reservation.guest_phone)
            existing.status = reservation.status.name
            reservation.id = str(existing.id)
        else:
            new_row = ReservationModel(
                guest_name=getattr(reservation, "guest_name", ""),
                guest_phone=str(reservation.guest_phone),
                status=reservation.status.name,
            )
            self.session.add(new_row)
            self.session.flush()
            reservation.id = str(new_row.id)

        self.session.commit()