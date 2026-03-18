"""Testes unitários para ConfirmReservationUseCase (Passo 3 - encapsulamento)."""
from datetime import date, timedelta

from app.application.use_cases.confirm_reservation import ConfirmReservationUseCase
from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.entities.reservation.stay_period import StayPeriod
from app.domain.value_objects.phone_number import PhoneNumber
from app.infrastructure.persistence.memory.reservation_repository_memory import (
    ReservationRepositoryMemory,
)


def test_get_formatted_summary_for_phone_returns_summary_when_reservation_exists():
    """get_formatted_summary_for_phone retorna resumo formatado quando há reserva."""
    repo = ReservationRepositoryMemory()
    hotel_id = "hotel-1"
    start = date.today() + timedelta(days=30)
    end = date.today() + timedelta(days=32)
    reservation = Reservation(
        reservation_id="1",
        guest_name="João Silva",
        hotel_id=hotel_id,
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.PENDING,
        room_number="101",
        stay_period=StayPeriod(start, end),
        total_amount=400.0,
    )
    repo.save(reservation, hotel_id)

    use_case = ConfirmReservationUseCase(reservation_repository=repo)
    result = use_case.get_formatted_summary_for_phone(
        hotel_id, "5561999999999"
    )

    assert result is not None
    assert "João Silva" in result
    assert "101" in result
    assert start.strftime("%d/%m/%Y") in result
    assert end.strftime("%d/%m/%Y") in result
    assert "400" in result


def test_get_formatted_summary_for_phone_returns_none_when_no_reservation():
    """get_formatted_summary_for_phone retorna None quando não há reserva."""
    repo = ReservationRepositoryMemory()
    hotel_id = "hotel-1"
    use_case = ConfirmReservationUseCase(reservation_repository=repo)

    result = use_case.get_formatted_summary_for_phone(
        hotel_id, "5561888888888"
    )

    assert result is None


def test_prepare_confirmation_message_when_no_reservation_uses_nao_accent():
    repo = ReservationRepositoryMemory()
    use_case = ConfirmReservationUseCase(reservation_repository=repo)

    result = use_case.prepare_confirmation(
        hotel_id="hotel-1",
        request_dto=type("DTO", (), {"phone": "5561999999999"})(),
    )

    assert result.success is False
    assert "não encontrada" in result.message.lower()


def test_prepare_confirmation_message_when_already_confirmed_uses_ja_accent():
    repo = ReservationRepositoryMemory()
    phone = "5561999999999"
    hotel_id = "hotel-1"
    repo.save(
        Reservation(
            reservation_id="1",
            guest_name="João",
            hotel_id=hotel_id,
            guest_phone=PhoneNumber(phone),
            status=ReservationStatus.CONFIRMED,
            room_number="101",
            stay_period=StayPeriod(date.today(), date.today() + timedelta(days=1)),
            total_amount=100.0,
        ),
        hotel_id=hotel_id,
    )

    use_case = ConfirmReservationUseCase(reservation_repository=repo)

    result = use_case.prepare_confirmation(
        hotel_id=hotel_id,
        request_dto=type("DTO", (), {"phone": phone})(),
    )

    assert result.success is True
    assert result.can_confirm is False
    assert "já está confirmada" in result.message.lower()
