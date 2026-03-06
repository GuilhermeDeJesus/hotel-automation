"""Testes unitários para job de no-show (Passo 9)."""
from datetime import date, timedelta

from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.entities.reservation.stay_period import StayPeriod
from app.domain.value_objects.phone_number import PhoneNumber
from app.infrastructure.persistence.memory.reservation_repository_memory import (
    ReservationRepositoryMemory,
)


def test_find_confirmed_past_checkin_date_returns_matching_reservations():
    """find_confirmed_past_checkin_date retorna reservas CONFIRMED com check-in no passado."""
    repo = ReservationRepositoryMemory()
    today = date.today()

    # Reserva CONFIRMED com check-in no passado - deve ser retornada
    past_start = today - timedelta(days=2)
    past_end = today + timedelta(days=1)
    r1 = Reservation(
        reservation_id="1",
        guest_name="João",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CONFIRMED,
        stay_period=StayPeriod(past_start, past_end, allow_past=True),
        room_number="101",
    )
    repo.save(r1)

    # Reserva CONFIRMED com check-in no futuro - NÃO deve ser retornada
    future_start = today + timedelta(days=2)
    future_end = today + timedelta(days=5)
    r2 = Reservation(
        reservation_id="2",
        guest_name="Maria",
        guest_phone=PhoneNumber("5561888888888"),
        status=ReservationStatus.CONFIRMED,
        stay_period=StayPeriod(future_start, future_end, allow_past=True),
        room_number="102",
    )
    repo.save(r2)

    # Reserva CHECKED_IN com check-in no passado - NÃO deve ser retornada (não é CONFIRMED)
    r3 = Reservation(
        reservation_id="3",
        guest_name="Pedro",
        guest_phone=PhoneNumber("5561777777777"),
        status=ReservationStatus.CHECKED_IN,
        stay_period=StayPeriod(past_start, past_end, allow_past=True),
        room_number="103",
    )
    repo.save(r3)

    result = repo.find_confirmed_past_checkin_date(today)

    assert len(result) == 1
    assert result[0].id == "1"
    assert result[0].status == ReservationStatus.CONFIRMED


def test_mark_as_no_show_updates_status():
    """mark_as_no_show altera status de CONFIRMED para NO_SHOW."""
    reservation = Reservation(
        reservation_id="1",
        guest_name="João",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.CONFIRMED,
        stay_period=StayPeriod(
            date.today() - timedelta(days=1),
            date.today() + timedelta(days=1),
            allow_past=True,
        ),
        room_number="101",
    )

    reservation.mark_as_no_show()

    assert reservation.status == ReservationStatus.NO_SHOW
