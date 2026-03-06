"""Testes unitários para CancelReservationUseCase (Passo 5)."""
from datetime import date, timedelta

from app.application.dto.cancel_reservation_request_dto import CancelReservationRequestDTO
from app.application.use_cases.cancel_reservation import CancelReservationUseCase
from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.entities.reservation.stay_period import StayPeriod
from app.domain.value_objects.phone_number import PhoneNumber
from app.infrastructure.persistence.memory.reservation_repository_memory import (
    ReservationRepositoryMemory,
)


def test_prepare_cancellation_without_reservation():
    """Quando não há reserva, retorna mensagem apropriada."""
    repo = ReservationRepositoryMemory()
    use_case = CancelReservationUseCase(reservation_repository=repo)

    response = use_case.prepare_cancellation(
        CancelReservationRequestDTO(phone="5561999999999")
    )

    assert response.success is False
    assert "não encontrada" in response.message
    assert response.can_cancel is False


def test_prepare_cancellation_pending_returns_can_cancel():
    """Reserva PENDING: pode cancelar, retorna resumo."""
    repo = ReservationRepositoryMemory()
    start = date.today() + timedelta(days=7)
    end = date.today() + timedelta(days=9)
    reservation = Reservation(
        reservation_id="1",
        guest_name="João",
        guest_phone=PhoneNumber("5561888777666"),
        status=ReservationStatus.PENDING,
        stay_period=StayPeriod(start, end),
        room_number="101",
        total_amount=400.0,
    )
    repo.save(reservation)

    use_case = CancelReservationUseCase(reservation_repository=repo)
    response = use_case.prepare_cancellation(
        CancelReservationRequestDTO(phone="5561888777666")
    )

    assert response.success is True
    assert response.can_cancel is True
    assert "João" in (response.summary or "")
    assert "101" in (response.summary or "")


def test_prepare_cancellation_checked_in_returns_cannot_cancel():
    """Reserva CHECKED_IN: não pode cancelar."""
    repo = ReservationRepositoryMemory()
    reservation = Reservation(
        reservation_id="1",
        guest_name="Maria",
        guest_phone=PhoneNumber("5561999991111"),
        status=ReservationStatus.CHECKED_IN,
        room_number="102",
    )
    repo.save(reservation)

    use_case = CancelReservationUseCase(reservation_repository=repo)
    response = use_case.prepare_cancellation(
        CancelReservationRequestDTO(phone="5561999991111")
    )

    assert response.success is False
    assert "check-in" in response.message.lower()
    assert response.can_cancel is False


def test_cancel_success():
    """Cancelamento bem-sucedido: persiste CANCELLED."""
    repo = ReservationRepositoryMemory()
    reservation = Reservation(
        reservation_id="1",
        guest_name="Pedro",
        guest_phone=PhoneNumber("5561777666555"),
        status=ReservationStatus.CONFIRMED,
        room_number="201",
    )
    repo.save(reservation)

    use_case = CancelReservationUseCase(reservation_repository=repo)
    response = use_case.cancel(CancelReservationRequestDTO(phone="5561777666555"))

    assert response.success is True
    assert "cancelada com sucesso" in response.message

    persisted = repo.find_by_phone_number("5561777666555")
    assert persisted is not None
    assert persisted.status == ReservationStatus.CANCELLED
