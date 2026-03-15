"""
SQL implementation of RoomRepository - manages room data access.
"""
import uuid
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

    def list_all(self, hotel_id: str) -> List[Room]:
        """List all active rooms for a hotel."""
        rooms = (
            self.session.query(RoomModel)
            .filter(RoomModel.hotel_id == hotel_id, RoomModel.is_active == True)
            .order_by(RoomModel.number)
            .all()
        )
        return [self._to_domain(r) for r in rooms]

    def get_by_number(self, hotel_id: str, room_number: str) -> Optional[Room]:
        """Retrieve room by number for a hotel."""
        room = (
            self.session.query(RoomModel)
            .filter_by(hotel_id=hotel_id, number=room_number, is_active=True)
            .first()
        )
        
        if not room:
            return None

        return self._to_domain(room)

    def find_available(
        self, hotel_id: str, check_in: date, check_out: date, exclude_room: Optional[str] = None
    ) -> List[Room]:
        """Find available rooms for a date range in a hotel."""
        # Query all active rooms for the hotel
        available_rooms = (
            self.session.query(RoomModel)
            .filter(RoomModel.hotel_id == hotel_id, RoomModel.is_active == True)
            .all()
        )

        available_list: List[Room] = []

        for room in available_rooms:
            # Exclude specific room if provided
            if exclude_room and room.number == exclude_room:
                continue

            # Check if room has conflicting reservations in the same hotel
            has_conflict = (
                self.session.query(ReservationModel)
                .filter(
                    ReservationModel.hotel_id == hotel_id,
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
        self,
        hotel_id: str,
        room_number: str,
        check_in: date,
        check_out: date,
        exclude_reservation_id: Optional[str] = None,
    ) -> bool:
        """Check if specific room is available for dates in a hotel."""
        # Check if room exists in the hotel
        room = (
            self.session.query(RoomModel)
            .filter_by(hotel_id=hotel_id, number=room_number, is_active=True)
            .first()
        )

        if not room:
            return False

        # Build conflict query for the hotel
        conflict_query = (
            self.session.query(ReservationModel)
            .filter(
                ReservationModel.hotel_id == hotel_id,
                ReservationModel.room_number == room_number,
                ReservationModel.status.in_(["CONFIRMED", "CHECKED_IN"]),
                and_(
                    ReservationModel.check_in_date < check_out,
                    ReservationModel.check_out_date > check_in,
                ),
            )
        )
        if exclude_reservation_id:
            conflict_query = conflict_query.filter(
                ReservationModel.id != exclude_reservation_id
            )
        has_conflict = conflict_query.first() is not None

        return not has_conflict

    def save(self, room: Room, hotel_id: str) -> Room:
        """Create or update a room for a hotel. Returns the saved room with id set on create."""
        existing = (
            self.session.query(RoomModel)
            .filter(RoomModel.hotel_id == hotel_id, RoomModel.number == room.number)
            .first()
        )
        if existing:
            existing.room_type = room.room_type
            existing.daily_rate = room.daily_rate
            existing.max_guests = room.max_guests
            existing.status = room.status
            self.session.commit()
            return self._to_domain(existing)
        new_id = str(uuid.uuid4())
        new_row = RoomModel(
            id=new_id,
            hotel_id=hotel_id,
            number=room.number,
            room_type=room.room_type,
            daily_rate=room.daily_rate,
            max_guests=room.max_guests,
            status=room.status,
            is_active=True,
        )
        self.session.add(new_row)
        self.session.commit()
        return Room(
            number=new_row.number,
            room_type=new_row.room_type,
            daily_rate=new_row.daily_rate,
            max_guests=new_row.max_guests,
            status=new_row.status,
            id=new_row.id,
        )

    def deactivate(self, hotel_id: str, room_number: str) -> bool:
        """Soft delete a room by setting is_active=False."""
        room = (
            self.session.query(RoomModel)
            .filter(RoomModel.hotel_id == hotel_id, RoomModel.number == room_number, RoomModel.is_active == True)
            .first()
        )
        if not room:
            return False
        room.is_active = False
        self.session.commit()
        return True

    @staticmethod
    def _to_domain(room_model: RoomModel) -> Room:
        return Room(
            number=room_model.number,
            room_type=room_model.room_type,
            daily_rate=room_model.daily_rate,
            max_guests=room_model.max_guests,
            status=room_model.status,
            id=room_model.id,
        )
