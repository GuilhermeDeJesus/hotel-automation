from typing import List, Optional
from datetime import datetime, date

import uuid
from sqlalchemy import func

from app.domain.entities.reservation.reservation import Reservation
from app.domain.repositories.reservation_repository import ReservationRepository
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.entities.reservation.stay_period import StayPeriod
from app.domain.value_objects.phone_number import PhoneNumber
from .models import ReservationModel

class ReservationRepositorySQL(ReservationRepository):
    def __init__(self, session):
        self.session = session

    @staticmethod
    def _normalize_phone(phone_number: str) -> str:
        return "".join(ch for ch in str(phone_number) if ch.isdigit())

    def find_by_id(self, reservation_id: str, hotel_id: str) -> Optional[Reservation]:
        model = (
            self.session.query(ReservationModel)
            .filter_by(id=str(reservation_id), hotel_id=hotel_id)
            .first()
        )
        if not model:
            return None
        return self._to_domain(model)

    def find_by_phone_number(self, phone_number: str, hotel_id: str) -> Optional[Reservation]:
        normalized_phone = self._normalize_phone(phone_number)
        reservation_model = (
            self.session
            .query(ReservationModel)
            .filter_by(guest_phone=normalized_phone, hotel_id=hotel_id)
            .order_by(ReservationModel.created_at.desc())
            .first()
        )
        if not reservation_model:
            return None
        return self._to_domain(reservation_model)

    def find_confirmed_past_checkin_date(self, reference_date: date, hotel_id: str) -> List[Reservation]:
        models = (
            self.session.query(ReservationModel)
            .filter(
                ReservationModel.status == "CONFIRMED",
                ReservationModel.check_in_date < reference_date,
                ReservationModel.hotel_id == hotel_id,
            )
            .all()
        )
        return [self._to_domain(m) for m in models]

    def list_reservations(
        self,
        hotel_id: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        status: Optional[str] = None,
        room_number: Optional[str] = None,
        limit: int = 100,
    ) -> List[Reservation]:
        query = self.session.query(ReservationModel).filter(ReservationModel.hotel_id == hotel_id)
        if from_date is not None:
            query = query.filter(ReservationModel.check_in_date >= from_date)
        if to_date is not None:
            query = query.filter(ReservationModel.check_in_date <= to_date)
        if status is not None:
            query = query.filter(ReservationModel.status == status.upper())
        if room_number is not None:
            query = query.filter(ReservationModel.room_number == room_number)
        models = (
            query.order_by(ReservationModel.check_in_date.desc(), ReservationModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._to_domain(m) for m in models]

    def count_by_status(
        self,
        hotel_id: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict[str, int]:
        query = (
            self.session.query(ReservationModel.status, func.count(ReservationModel.id))
            .filter(~ReservationModel.status.in_(["CANCELLED", "NO_SHOW"]))
            .filter(ReservationModel.hotel_id == hotel_id)
        )
        if from_date is not None:
            query = query.filter(ReservationModel.check_in_date >= from_date)
        if to_date is not None:
            query = query.filter(ReservationModel.check_in_date <= to_date)
        rows = query.group_by(ReservationModel.status).all()
        return {str(status).upper(): int(count) for status, count in rows}

    @staticmethod
    def _to_domain(reservation_model: ReservationModel) -> Reservation:
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
            hotel_id=reservation_model.hotel_id,
            guest_phone=PhoneNumber(reservation_model.guest_phone),
            status=status_enum,
            stay_period=stay_period,
            room_number=reservation_model.room_number,
            total_amount=reservation_model.total_amount,
            created_at=reservation_model.created_at,
            checked_in_at=reservation_model.checked_in_at,
            checked_out_at=reservation_model.checked_out_at,
            guest_document=getattr(reservation_model, "guest_document", None),
            estimated_arrival_time=getattr(reservation_model, "estimated_arrival_time", None),
            pre_checkin_completed_at=getattr(reservation_model, "pre_checkin_completed_at", None),
            digital_key_code=getattr(reservation_model, "digital_key_code", None),
            consent_terms_accepted_at=getattr(reservation_model, "consent_terms_accepted_at", None),
            consent_marketing=getattr(reservation_model, "consent_marketing", False) or False,
        )

    def save(self, reservation: Reservation, hotel_id: str) -> None:
        """Insert or update a reservation for a specific hotel."""
        existing = None
        if reservation.id:
            existing = (
                self.session.query(ReservationModel)
                .filter_by(id=str(reservation.id), hotel_id=hotel_id)
                .first()
            )
        if existing is None:
            existing = (
                self.session
                .query(ReservationModel)
                .filter_by(guest_phone=str(reservation.guest_phone), hotel_id=hotel_id)
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
            existing.guest_document = getattr(reservation, "guest_document", None)
            existing.estimated_arrival_time = getattr(reservation, "estimated_arrival_time", None)
            existing.pre_checkin_completed_at = getattr(reservation, "pre_checkin_completed_at", None)
            existing.digital_key_code = getattr(reservation, "digital_key_code", None)
            existing.consent_terms_accepted_at = getattr(reservation, "consent_terms_accepted_at", None)
            existing.consent_marketing = getattr(reservation, "consent_marketing", False)
            existing.updated_at = datetime.now()
            reservation.id = str(existing.id)
        else:
            new_row = ReservationModel(
                id=str(reservation.id) if reservation.id else str(uuid.uuid4()),
                guest_name=getattr(reservation, "guest_name", ""),
                hotel_id=hotel_id,
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