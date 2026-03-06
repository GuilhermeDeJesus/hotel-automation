"""Testes unitários para Reservation.extend_stay (Passo 8 - domínio)."""
from datetime import date

import pytest

from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.entities.reservation.stay_period import StayPeriod
from app.domain.value_objects.phone_number import PhoneNumber
from app.domain import exceptions


def test_extend_stay_allowed_when_confirmed():
    """Extensão permitida quando status é CONFIRMED."""
    period = StayPeriod(date(2025, 4, 20), date(2025, 4, 23), allow_past=True)
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CONFIRMED,
        stay_period=period,
        room_number="101",
        total_amount=300.0,
    )
    reservation.extend_stay(date(2025, 4, 25), daily_rate=100.0)
    assert reservation.stay_period.start == date(2025, 4, 20)
    assert reservation.stay_period.end == date(2025, 4, 25)
    assert reservation.total_amount == 500.0  # 5 noites * 100


def test_extend_stay_allowed_when_checked_in():
    """Extensão permitida quando status é CHECKED_IN."""
    period = StayPeriod(date(2025, 4, 20), date(2025, 4, 23), allow_past=True)
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CHECKED_IN,
        stay_period=period,
        room_number="101",
        total_amount=300.0,
    )
    reservation.extend_stay(date(2025, 4, 26), daily_rate=150.0)
    assert reservation.stay_period.end == date(2025, 4, 26)
    assert reservation.total_amount == 900.0  # 6 noites * 150


def test_extend_stay_raises_when_new_checkout_not_after_current():
    """Extensão proibida quando nova data não é após o check-out atual."""
    period = StayPeriod(date(2025, 4, 20), date(2025, 4, 23), allow_past=True)
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CHECKED_IN,
        stay_period=period,
        room_number="101",
    )
    with pytest.raises(exceptions.InvalidExtendStayDate) as exc_info:
        reservation.extend_stay(date(2025, 4, 23), daily_rate=100.0)
    assert "deve ser após" in str(exc_info.value)

    with pytest.raises(exceptions.InvalidExtendStayDate) as exc_info2:
        reservation.extend_stay(date(2025, 4, 22), daily_rate=100.0)
    assert "deve ser após" in str(exc_info2.value)


def test_extend_stay_raises_when_pending():
    """Extensão proibida quando status é PENDING (ainda não fez check-in)."""
    period = StayPeriod(date(2025, 4, 20), date(2025, 4, 23), allow_past=True)
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.PENDING,
        stay_period=period,
        room_number="101",
    )
    with pytest.raises(exceptions.InvalidExtendStayState) as exc_info:
        reservation.extend_stay(date(2025, 4, 25), daily_rate=100.0)
    assert "confirmadas ou com check-in" in str(exc_info.value)


def test_extend_stay_raises_when_checked_out():
    """Extensão proibida quando já fez check-out."""
    period = StayPeriod(date(2025, 4, 20), date(2025, 4, 23), allow_past=True)
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CHECKED_OUT,
        stay_period=period,
        room_number="101",
    )
    with pytest.raises(exceptions.InvalidExtendStayState) as exc_info:
        reservation.extend_stay(date(2025, 4, 25), daily_rate=100.0)
    assert "confirmadas ou com check-in" in str(exc_info.value)


def test_extend_stay_raises_when_no_stay_period():
    """Extensão proibida quando reserva não tem período definido."""
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CHECKED_IN,
        stay_period=None,
        room_number="101",
    )
    with pytest.raises(exceptions.InvalidExtendStayDate) as exc_info:
        reservation.extend_stay(date(2025, 4, 25), daily_rate=100.0)
    assert "sem período" in str(exc_info.value)
