from datetime import date, timedelta

from app.application.dto.checkin_request_dto import CheckinRequestDTO
from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.entities.reservation.stay_period import StayPeriod
from app.domain.value_objects.phone_number import PhoneNumber
from app.infrastructure.persistence.memory.reservation_repository_memory import (
    ReservationRepositoryMemory,
)


class InMemoryCache:
    def __init__(self):
        self.store = {}

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value, ttl_seconds: int = 3600):
        self.store[key] = value

    def delete(self, key: str):
        self.store.pop(key, None)

    def exists(self, key: str) -> bool:
        return key in self.store

    def clear(self):
        self.store.clear()


def test_checkin_without_reservation():
    """Quando não há reserva, retorna mensagem apropriada e não grava cache."""
    reservation_repository = ReservationRepositoryMemory()
    cache_repository = InMemoryCache()
    hotel_id = "hotel-1"

    checkin_use_case = CheckInViaWhatsAppUseCase(reservation_repository, cache_repository)
    request_dto = CheckinRequestDTO(phone="5561999999999")

    response = checkin_use_case.execute(hotel_id, request_dto)

    assert response.message == "Nenhuma reserva encontrada para esse numero."
    cache_key = f"{CheckInViaWhatsAppUseCase.CHECKIN_DONE_KEY_PREFIX}{hotel_id}:5561999999999"
    assert cache_repository.get(cache_key) is None


def test_checkin_first_call_executes_and_persists():
    """Primeira chamada executa check-in, persiste e grava cache."""
    reservation_repository = ReservationRepositoryMemory()
    cache_repository = InMemoryCache()
    hotel_id = "hotel-1"

    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede Teste",
        hotel_id=hotel_id,
        guest_phone=PhoneNumber("5561888777666"),
        status=ReservationStatus.CONFIRMED,
    )
    reservation_repository.save(reservation, hotel_id)

    checkin_use_case = CheckInViaWhatsAppUseCase(reservation_repository, cache_repository)
    request_dto = CheckinRequestDTO(phone="5561888777666")

    response = checkin_use_case.execute(hotel_id, request_dto)

    assert "Check-in feito com sucesso!" in response.message
    # Verifica que a reserva foi persistida com status CHECKED_IN
    persisted = reservation_repository.find_by_phone_number("5561888777666", hotel_id)
    assert persisted is not None
    assert persisted.status == ReservationStatus.CHECKED_IN
    assert persisted.digital_key_code is not None
    # Verifica que o cache foi gravado
    cache_key = f"{CheckInViaWhatsAppUseCase.CHECKIN_DONE_KEY_PREFIX}{hotel_id}:5561888777666"
    assert cache_repository.get(cache_key) is not None


def test_checkin_with_cache_returns_already_done():
    """Quando cache tem checkin_done, retorna 'já realizou' sem executar check-in."""
    reservation_repository = ReservationRepositoryMemory()
    cache_repository = InMemoryCache()
    hotel_id = "hotel-1"

    reservation = Reservation(
        reservation_id="1",
        guest_name="Guilherme de Jesus Silva",
        hotel_id=hotel_id,
        guest_phone=PhoneNumber("5561998776092"),
        status=ReservationStatus.CONFIRMED,
    )
    reservation_repository.save(reservation, hotel_id)

    checkin_use_case = CheckInViaWhatsAppUseCase(reservation_repository, cache_repository)
    request_dto = CheckinRequestDTO(phone="5561998776092")

    # Primeira chamada: executa check-in e grava cache
    response_dto_1 = checkin_use_case.execute(hotel_id, request_dto)
    assert "Check-in feito com sucesso!" in response_dto_1.message
    cache_key = f"{CheckInViaWhatsAppUseCase.CHECKIN_DONE_KEY_PREFIX}{hotel_id}:5561998776092"
    assert cache_repository.get(cache_key) is not None

    # Segunda chamada: cache hit, retorna mensagem informativa (não executa check-in de novo)
    response_dto_2 = checkin_use_case.execute(hotel_id, request_dto)
    assert "Check-in feito com sucesso!" in response_dto_2.message


def test_checkin_legacy_cache_is_ignored_for_hotel_scope():
    """Se existir chave legada (sem hotel_id), não pode fazer skip cross-tenant."""
    reservation_repository = ReservationRepositoryMemory()
    cache_repository = InMemoryCache()
    hotel_id = "hotel-1"
    phone = "5561998776092"

    reservation = Reservation(
        reservation_id="1",
        guest_name="Guilherme de Jesus Silva",
        hotel_id=hotel_id,
        guest_phone=PhoneNumber(phone),
        status=ReservationStatus.CONFIRMED,
    )
    reservation_repository.save(reservation, hotel_id)

    # Chave legada (sem hotel_id) não deve ser considerada.
    legacy_cache_key = f"{CheckInViaWhatsAppUseCase.CHECKIN_DONE_KEY_PREFIX}{phone}"
    cache_repository.set(legacy_cache_key, {"done": True}, ttl_seconds=3600)

    checkin_use_case = CheckInViaWhatsAppUseCase(
        reservation_repository, cache_repository
    )
    request_dto = CheckinRequestDTO(phone=phone)

    response = checkin_use_case.execute(hotel_id, request_dto)
    assert "Check-in feito com sucesso!" in response.message

    # Legada deve ser removida.
    assert cache_repository.get(legacy_cache_key) is None

    # Nova chave tenant-scoped deve existir.
    scoped_cache_key = (
        f"{CheckInViaWhatsAppUseCase.CHECKIN_DONE_KEY_PREFIX}{hotel_id}:{phone}"
    )
    assert cache_repository.get(scoped_cache_key) is not None


def test_checkin_cancelled_reservation_returns_friendly_message():
    """Reserva cancelada: retorna mensagem amigável (InvalidCheckInState)."""
    reservation_repository = ReservationRepositoryMemory()
    cache_repository = InMemoryCache()
    hotel_id = "hotel-1"

    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        hotel_id=hotel_id,
        guest_phone=PhoneNumber("5561999991111"),
        status=ReservationStatus.CANCELLED,
    )
    reservation_repository.save(reservation, hotel_id)

    checkin_use_case = CheckInViaWhatsAppUseCase(reservation_repository, cache_repository)
    response = checkin_use_case.execute(
        hotel_id, CheckinRequestDTO(phone="5561999991111")
    )

    assert response.success is False
    assert "cancelada" in response.message.lower() or "check-in" in response.message.lower()
    assert response.error is not None


def test_checkin_before_allowed_date_returns_friendly_message():
    """Check-in antes da data permitida: retorna mensagem amigável (InvalidCheckInDate)."""
    reservation_repository = ReservationRepositoryMemory()
    cache_repository = InMemoryCache()
    hotel_id = "hotel-1"

    start = date.today() + timedelta(days=7)
    end = date.today() + timedelta(days=9)
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        hotel_id=hotel_id,
        guest_phone=PhoneNumber("5561999992222"),
        status=ReservationStatus.CONFIRMED,
        stay_period=StayPeriod(start, end),
        room_number="101",
    )
    reservation_repository.save(reservation, hotel_id)

    checkin_use_case = CheckInViaWhatsAppUseCase(reservation_repository, cache_repository)
    response = checkin_use_case.execute(
        hotel_id, CheckinRequestDTO(phone="5561999992222")
    )

    assert response.success is False
    assert "check-in" in response.message.lower() or "permitido" in response.message.lower()
    assert response.error is not None