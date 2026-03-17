"""List reservations with optional filters."""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

from app.domain.repositories.reservation_repository import ReservationRepository


class ListReservationsUseCase:
    def __init__(self, reservation_repository: ReservationRepository):
        self.reservation_repository = reservation_repository

    def execute(
        self,
        hotel_id: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        status: Optional[str] = None,
        room_number: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        reservations = self.reservation_repository.list_reservations(
            hotel_id=hotel_id,
            from_date=from_date,
            to_date=to_date,
            status=status,
            room_number=room_number,
            limit=limit,
        )
        return [self._to_dict(r) for r in reservations]

    @staticmethod
    def _to_dict(r) -> dict[str, Any]:
        return {
            "id": r.id,
            "guest_name": r.guest_name,
            "guest_phone": str(r.guest_phone),
            "status": r.status.name,
            "check_in_date": r.stay_period.start.isoformat() if r.stay_period else None,
            "check_out_date": r.stay_period.end.isoformat() if r.stay_period else None,
            "room_number": r.room_number,
            "total_amount": r.total_amount,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "checked_in_at": r.checked_in_at.isoformat() if r.checked_in_at else None,
            "checked_out_at": r.checked_out_at.isoformat() if r.checked_out_at else None,
        }

