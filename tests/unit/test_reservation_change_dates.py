"""Testes unitários para Reservation.change_dates (Passo 7 - domínio)."""
from datetime import date

import pytest

from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.entities.reservation.stay_period import StayPeriod
from app.domain.value_objects.phone_number import PhoneNumber
from app.domain import exceptions


def test_change_dates_allowed_when_pending():
    """Alteração de datas permitida quando status é PENDING."""
    period = StayPeriod(date(2025, 4, 20), date(2025, 4, 23), allow_past=True)
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.PENDING,
        stay_period=period,
        room_number="101",
        total_amount=300.0,
    )
    new_period = StayPeriod(date(2025, 4, 25), date(2025, 4, 28), allow_past=True)
    reservation.change_dates(new_period, daily_rate=100.0)
    assert reservation.stay_period == new_period
    assert reservation.total_amount == 300.0  # 3 noites * 100


def test_change_dates_allowed_when_confirmed():
    """Alteração de datas permitida quando status é CONFIRMED."""
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
    new_period = StayPeriod(date(2025, 5, 1), date(2025, 5, 5), allow_past=True)
    reservation.change_dates(new_period, daily_rate=150.0)
    assert reservation.stay_period == new_period
    assert reservation.total_amount == 600.0  # 4 noites * 150


def test_change_dates_raises_when_checked_in():
    """Alteração de datas proibida quando já fez check-in."""
    period = StayPeriod(date(2025, 4, 20), date(2025, 4, 23), allow_past=True)
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CHECKED_IN,
        stay_period=period,
        room_number="101",
    )
    new_period = StayPeriod(date(2025, 4, 25), date(2025, 4, 28), allow_past=True)
    with pytest.raises(exceptions.InvalidDatesChangeState) as exc_info:
        reservation.change_dates(new_period, daily_rate=100.0)
    assert "antes do check-in" in str(exc_info.value)


def test_change_dates_raises_when_checked_out():
    """Alteração de datas proibida quando já fez check-out."""
    period = StayPeriod(date(2025, 4, 20), date(2025, 4, 23), allow_past=True)
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CHECKED_OUT,
        stay_period=period,
        room_number="101",
    )
    new_period = StayPeriod(date(2025, 4, 25), date(2025, 4, 28), allow_past=True)
    with pytest.raises(exceptions.InvalidDatesChangeState) as exc_info:
        reservation.change_dates(new_period, daily_rate=100.0)
    assert "antes do check-in" in str(exc_info.value)


def test_change_dates_raises_when_cancelled():
    """Alteração de datas proibida quando reserva está cancelada."""
    period = StayPeriod(date(2025, 4, 20), date(2025, 4, 23), allow_past=True)
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CANCELLED,
        stay_period=period,
        room_number="101",
    )
    new_period = StayPeriod(date(2025, 4, 25), date(2025, 4, 28), allow_past=True)
    with pytest.raises(exceptions.InvalidDatesChangeState) as exc_info:
        reservation.change_dates(new_period, daily_rate=100.0)
    assert "antes do check-in" in str(exc_info.value)
