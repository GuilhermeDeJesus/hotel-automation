"""Testes unitários para CheckoutViaWhatsAppUseCase (Passo 4)."""
from app.application.dto.checkout_request_dto import CheckoutRequestDTO
from app.application.use_cases.checkout_via_whatsapp import CheckoutViaWhatsAppUseCase
from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.value_objects.phone_number import PhoneNumber
from app.infrastructure.persistence.memory.reservation_repository_memory import (
    ReservationRepositoryMemory,
)


def test_checkout_without_reservation():
    """Quando não há reserva, retorna mensagem apropriada."""
    repo = ReservationRepositoryMemory()
    use_case = CheckoutViaWhatsAppUseCase(reservation_repository=repo)
    hotel_id = "hotel-1"

    response = use_case.execute(
        hotel_id, CheckoutRequestDTO(phone="5561999999999")
    )

    assert response.success is False
    assert "Nenhuma reserva encontrada" in response.message


def test_checkout_success():
    """Check-out bem-sucedido: persiste e retorna mensagem de sucesso."""
    repo = ReservationRepositoryMemory()
    hotel_id = "hotel-1"
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        hotel_id=hotel_id,
        guest_phone=PhoneNumber("5561888777666"),
        status=ReservationStatus.CHECKED_IN,
        room_number="101",
    )
    repo.save(reservation, hotel_id)

    use_case = CheckoutViaWhatsAppUseCase(reservation_repository=repo)
    response = use_case.execute(
        hotel_id, CheckoutRequestDTO(phone="5561888777666")
    )

    assert response.success is True
    assert "Check-out realizado com sucesso" in response.message

    persisted = repo.find_by_phone_number("5561888777666", hotel_id)
    assert persisted is not None
    assert persisted.status == ReservationStatus.CHECKED_OUT


def test_checkout_before_checkin_returns_friendly_message():
    """Check-out sem ter feito check-in: retorna mensagem amigável (InvalidCheckOutState)."""
    repo = ReservationRepositoryMemory()
    hotel_id = "hotel-1"
    reservation = Reservation(
        reservation_id="1",
        guest_name="Hospede",
        hotel_id=hotel_id,
        guest_phone=PhoneNumber("5561999991111"),
        status=ReservationStatus.CONFIRMED,
        room_number="101",
    )
    repo.save(reservation, hotel_id)

    use_case = CheckoutViaWhatsAppUseCase(reservation_repository=repo)
    response = use_case.execute(
        hotel_id, CheckoutRequestDTO(phone="5561999991111")
    )

    assert response.success is False
    assert "check-out" in response.message.lower() or "check-in" in response.message.lower()
    assert response.error is not None
