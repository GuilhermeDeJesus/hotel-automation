from typing import Optional
from datetime import datetime
import uuid

from app.domain.entities.reservation.reservation import Reservation
from app.domain.repositories.reservation_repository import ReservationRepository
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.entities.reservation.stay_period import StayPeriod
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
            .order_by(ReservationModel.created_at.desc())
            .first()
        )
        if not reservation_model:
            return None

        status_enum = ReservationStatus[reservation_model.status]
        stay_period = None
        if reservation_model.check_in_date and reservation_model.check_out_date:
            stay_period = StayPeriod(
                reservation_model.check_in_date,
                reservation_model.check_out_date,
                allow_past=True,
            )

        return Reservation(
            reservation_id=str(reservation_model.id),
            guest_name=reservation_model.guest_name,
            guest_phone=PhoneNumber(reservation_model.guest_phone),
            status=status_enum,
            stay_period=stay_period,
            room_number=reservation_model.room_number,
            total_amount=reservation_model.total_amount,
            created_at=reservation_model.created_at,
            checked_in_at=reservation_model.checked_in_at,
            checked_out_at=reservation_model.checked_out_at,
        )

    def save(self, reservation: Reservation) -> None:
        """Insert or update a reservation based on id or phone.
        """
        existing: ReservationModel | None = None

        if reservation.id:
            existing = self.session.get(ReservationModel, str(reservation.id))

        if existing is None:
            existing = (
                self.session
                .query(ReservationModel)
                .filter_by(guest_phone=str(reservation.guest_phone))
                .order_by(ReservationModel.created_at.desc())
                .first()
            )

        if existing:
            existing.guest_name = reservation.guest_name
            existing.guest_phone = str(reservation.guest_phone)
            existing.status = reservation.status.name
            existing.room_number = reservation.room_number
            existing.total_amount = reservation.total_amount
            if reservation.stay_period:
                existing.check_in_date = reservation.stay_period.start
                existing.check_out_date = reservation.stay_period.end
            existing.checked_in_at = reservation.checked_in_at
            existing.checked_out_at = reservation.checked_out_at
            existing.updated_at = datetime.now()
            reservation.id = str(existing.id)
        else:
            new_row = ReservationModel(
                id=str(reservation.id) if reservation.id else str(uuid.uuid4()),
                guest_name=getattr(reservation, "guest_name", ""),
                guest_phone=str(reservation.guest_phone),
                status=reservation.status.name,
                room_number=reservation.room_number,
                total_amount=reservation.total_amount,
                check_in_date=reservation.stay_period.start if reservation.stay_period else None,
                check_out_date=reservation.stay_period.end if reservation.stay_period else None,
                checked_in_at=reservation.checked_in_at,
                checked_out_at=reservation.checked_out_at,
            )
            self.session.add(new_row)
            self.session.flush()
            reservation.id = str(new_row.id)

        self.session.commit()