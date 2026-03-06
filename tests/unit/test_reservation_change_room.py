"""Testes unitários para Reservation.change_room (Passo 2 - domínio)."""
import pytest

from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.value_objects.phone_number import PhoneNumber
from app.domain import exceptions


def test_change_room_allowed_when_pending():
    """Troca de quarto permitida quando status é PENDING."""
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.PENDING,
        room_number="101",
    )
    reservation.change_room("102")
    assert reservation.room_number == "102"


def test_change_room_allowed_when_confirmed():
    """Troca de quarto permitida quando status é CONFIRMED."""
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CONFIRMED,
        room_number="101",
    )
    reservation.change_room("201")
    assert reservation.room_number == "201"


def test_change_room_raises_when_checked_in():
    """Troca de quarto proibida quando já fez check-in."""
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CHECKED_IN,
        room_number="101",
    )
    with pytest.raises(exceptions.InvalidRoomChangeState) as exc_info:
        reservation.change_room("102")
    assert "antes do check-in" in str(exc_info.value)


def test_change_room_raises_when_checked_out():
    """Troca de quarto proibida quando já fez check-out."""
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CHECKED_OUT,
        room_number="101",
    )
    with pytest.raises(exceptions.InvalidRoomChangeState) as exc_info:
        reservation.change_room("102")
    assert "antes do check-in" in str(exc_info.value)


def test_change_room_raises_when_cancelled():
    """Troca de quarto proibida quando reserva está cancelada."""
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CANCELLED,
        room_number="101",
    )
    with pytest.raises(exceptions.InvalidRoomChangeState) as exc_info:
        reservation.change_room("102")
    assert "antes do check-in" in str(exc_info.value)
