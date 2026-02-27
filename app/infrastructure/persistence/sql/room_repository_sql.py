"""
SQL implementation of RoomRepository - manages room data access.
"""
from typing import Optional, List
from datetime import date
from sqlalchemy import and_

from app.domain.entities.room.room import Room
from app.domain.repositories.room_repository import RoomRepository
from .models import RoomModel, ReservationModel


class RoomRepositorySQL(RoomRepository):
    """SQL-based room repository implementation."""

    def __init__(self, session):
        self.session = session

    def get_by_number(self, room_number: str) -> Optional[Room]:
        """Retrieve room by number."""
        room = (
            self.session.query(RoomModel)
            .filter_by(number=room_number, is_active=True)
            .first()
        )
        
        if not room:
            return None

        return self._to_domain(room)

    def find_available(
        self, check_in: date, check_out: date, exclude_room: Optional[str] = None
    ) -> List[Room]:
        """Find available rooms for a date range."""
        # Query all active rooms
        available_rooms = (
            self.session.query(RoomModel)
            .filter(RoomModel.is_active == True)
            .all()
        )

        available_list: List[Room] = []

        for room in available_rooms:
            # Exclude specific room if provided
            if exclude_room and room.number == exclude_room:
                continue

            # Check if room has conflicting reservations
            has_conflict = (
                self.session.query(ReservationModel)
                .filter(
                    ReservationModel.room_number == room.number,
                    ReservationModel.status.in_(["CONFIRMED", "CHECKED_IN"]),
                    # Check overlap: existing check_in < new check_out AND existing check_out > new check_in
                    and_(
                        ReservationModel.check_in_date < check_out,
                        ReservationModel.check_out_date > check_in,
                    ),
                )
                .first()
            ) is not None

            if not has_conflict:
                available_list.append(self._to_domain(room))

        return available_list

    def is_available(
        self, room_number: str, check_in: date, check_out: date
    ) -> bool:
        """Check if specific room is available for dates."""
        # Check if room exists
        room = (
            self.session.query(RoomModel)
            .filter_by(number=room_number, is_active=True)
            .first()
        )

        if not room:
            return False

        # Check for conflicting reservations
        has_conflict = (
            self.session.query(ReservationModel)
            .filter(
                ReservationModel.room_number == room_number,
                ReservationModel.status.in_(["CONFIRMED", "CHECKED_IN"]),
                and_(
                    ReservationModel.check_in_date < check_out,
                    ReservationModel.check_out_date > check_in,
                ),
            )
            .first()
        ) is not None

        return not has_conflict

    @staticmethod
    def _to_domain(room_model: RoomModel) -> Room:
        return Room(
            number=room_model.number,
            room_type=room_model.room_type,
            daily_rate=room_model.daily_rate,
            max_guests=room_model.max_guests,
            status=room_model.status,
        )
