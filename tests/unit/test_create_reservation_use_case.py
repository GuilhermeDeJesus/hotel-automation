"""Testes unitários para CreateReservationUseCase (Passo 6)."""
from datetime import date, timedelta

from app.application.dto.create_reservation_request_dto import CreateReservationRequestDTO
from app.application.use_cases.create_reservation import CreateReservationUseCase
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.infrastructure.persistence.memory.reservation_repository_memory import (
    ReservationRepositoryMemory,
)


class RoomRepositoryStub:
    """Stub com quartos fixos para teste."""

    def __init__(self, rooms=None):
        self._rooms = rooms or [
            type("Room", (), {"number": "101", "room_type": "SINGLE", "daily_rate": 150.0})(),
            type("Room", (), {"number": "102", "room_type": "DOUBLE", "daily_rate": 250.0})(),
        ]

    def get_by_number(self, room_number: str):
        for r in self._rooms:
            if r.number == room_number:
                return r
        return None

    def find_available(self, check_in, check_out, exclude_room=None):
        return [r for r in self._rooms if r.number != exclude_room]

    def is_available(self, room_number: str, check_in, check_out) -> bool:
        return self.get_by_number(room_number) is not None


def test_create_reservation_success():
    """Cria reserva PENDING e persiste."""
    start = date.today() + timedelta(days=10)
    end = date.today() + timedelta(days=12)
    reservation_repo = ReservationRepositoryMemory()
    room_repo = RoomRepositoryStub()

    use_case = CreateReservationUseCase(
        reservation_repository=reservation_repo,
        room_repository=room_repo,
    )

    response = use_case.create(
        CreateReservationRequestDTO(
            phone="5561999999999",
            check_in=start,
            check_out=end,
            room_number="101",
            guest_name="Maria Santos",
        )
    )

    assert response.success is True
    assert "criada" in response.message.lower()
    assert response.reservation_id is not None

    persisted = reservation_repo.find_by_phone_number("5561999999999")
    assert persisted is not None
    assert persisted.status == ReservationStatus.PENDING
    assert persisted.guest_name == "Maria Santos"
    assert persisted.room_number == "101"
    assert persisted.total_amount == 300.0  # 2 noites * 150


def test_create_reservation_room_not_found():
    """Quarto inexistente retorna erro."""
    start = date.today() + timedelta(days=10)
    end = date.today() + timedelta(days=12)
    reservation_repo = ReservationRepositoryMemory()
    room_repo = RoomRepositoryStub()

    use_case = CreateReservationUseCase(
        reservation_repository=reservation_repo,
        room_repository=room_repo,
    )

    response = use_case.create(
        CreateReservationRequestDTO(
            phone="5561999999999",
            check_in=start,
            check_out=end,
            room_number="999",
            guest_name="João",
        )
    )

    assert response.success is False
    assert "não encontrado" in response.message.lower()


def test_check_availability_returns_rooms():
    """check_availability retorna quartos disponíveis."""
    start = date.today() + timedelta(days=10)
    end = date.today() + timedelta(days=12)
    reservation_repo = ReservationRepositoryMemory()
    room_repo = RoomRepositoryStub()

    use_case = CreateReservationUseCase(
        reservation_repository=reservation_repo,
        room_repository=room_repo,
    )

    rooms = use_case.check_availability(start, end)
    assert len(rooms) >= 1
    assert any(r.number == "101" for r in rooms)
