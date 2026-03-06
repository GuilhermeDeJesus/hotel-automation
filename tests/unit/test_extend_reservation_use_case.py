"""Testes unitários para ExtendReservationUseCase (Passo 8)."""
from datetime import date, timedelta

from app.application.dto.extend_reservation_request_dto import ExtendReservationRequestDTO
from app.application.use_cases.extend_reservation import ExtendReservationUseCase
from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.entities.reservation.stay_period import StayPeriod
from app.domain.value_objects.phone_number import PhoneNumber
from app.infrastructure.persistence.memory.reservation_repository_memory import (
    ReservationRepositoryMemory,
)


class MockRoomRepository:
    def __init__(self, daily_rate: float = 100.0, room_available: bool = True):
        self.daily_rate = daily_rate
        self.room_available = room_available

    def get_by_number(self, room_number: str):
        from app.domain.entities.room.room import Room
        return Room(
            number=room_number,
            room_type="DOUBLE",
            daily_rate=self.daily_rate,
            max_guests=2,
            status="AVAILABLE",
        )

    def is_available(
        self,
        room_number: str,
        check_in: date,
        check_out: date,
        exclude_reservation_id: str | None = None,
    ) -> bool:
        return self.room_available


def test_prepare_extension_returns_can_extend_when_checked_in():
    """prepare_extension retorna can_extend=True quando reserva está CHECKED_IN."""
    repo = ReservationRepositoryMemory()
    start = date.today() - timedelta(days=1)
    end = date.today() + timedelta(days=2)
    reservation = Reservation(
        reservation_id="1",
        guest_name="João",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CHECKED_IN,
        stay_period=StayPeriod(start, end, allow_past=True),
        room_number="101",
        total_amount=300.0,
    )
    repo.save(reservation)

    room_repo = MockRoomRepository()
    use_case = ExtendReservationUseCase(
        reservation_repository=repo,
        room_repository=room_repo,
    )

    response = use_case.prepare_extension(
        ExtendReservationRequestDTO(phone="5561999999999")
    )

    assert response.success is True
    assert response.can_extend is True
    assert response.current_checkout == end


def test_prepare_extension_fails_when_no_reservation():
    """prepare_extension falha quando não há reserva."""
    repo = ReservationRepositoryMemory()
    room_repo = MockRoomRepository()
    use_case = ExtendReservationUseCase(
        reservation_repository=repo,
        room_repository=room_repo,
    )

    response = use_case.prepare_extension(
        ExtendReservationRequestDTO(phone="5561888888888")
    )

    assert response.success is False
    assert response.can_extend is False


def test_prepare_extension_fails_when_checked_out():
    """prepare_extension falha quando reserva já fez check-out."""
    repo = ReservationRepositoryMemory()
    start = date.today() - timedelta(days=3)
    end = date.today() - timedelta(days=1)
    reservation = Reservation(
        reservation_id="1",
        guest_name="João",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CHECKED_OUT,
        stay_period=StayPeriod(start, end, allow_past=True),
        room_number="101",
    )
    repo.save(reservation)

    room_repo = MockRoomRepository()
    use_case = ExtendReservationUseCase(
        reservation_repository=repo,
        room_repository=room_repo,
    )

    response = use_case.prepare_extension(
        ExtendReservationRequestDTO(phone="5561999999999")
    )

    assert response.success is False
    assert "CHECKED_OUT" in response.message


def test_extend_updates_reservation_when_valid():
    """extend atualiza reserva quando dados são válidos."""
    repo = ReservationRepositoryMemory()
    start = date.today() - timedelta(days=1)
    end = date.today() + timedelta(days=2)
    reservation = Reservation(
        reservation_id="1",
        guest_name="João",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CHECKED_IN,
        stay_period=StayPeriod(start, end, allow_past=True),
        room_number="101",
        total_amount=300.0,
    )
    repo.save(reservation)

    class AvailableRoomRepo:
        def get_by_number(self, room_number: str):
            from app.domain.entities.room.room import Room
            return Room(
                number=room_number,
                room_type="DOUBLE",
                daily_rate=100.0,
                max_guests=2,
                status="AVAILABLE",
            )

        def is_available(self, *args, **kwargs) -> bool:
            return True

    use_case = ExtendReservationUseCase(
        reservation_repository=repo,
        room_repository=AvailableRoomRepo(),
    )

    new_checkout = date.today() + timedelta(days=5)
    response = use_case.extend(
        ExtendReservationRequestDTO(phone="5561999999999", new_checkout=new_checkout)
    )

    assert response.success is True
    updated = repo.find_by_phone_number("5561999999999")
    assert updated.stay_period.end == new_checkout
    assert updated.total_amount == 600.0  # 6 noites * 100
