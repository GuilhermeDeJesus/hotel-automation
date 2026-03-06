"""Testes para configuração de pagamento do hotel (10.6/10.7)."""
from datetime import date, timedelta

from app.application.dto.whatsapp_message_request_dto import WhatsAppMessageRequestDTO
from app.application.use_cases.handle_whatsapp_message import HandleWhatsAppMessageUseCase
from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.entities.reservation.stay_period import StayPeriod
from app.domain.value_objects.phone_number import PhoneNumber
from app.infrastructure.persistence.memory.reservation_repository_memory import (
    ReservationRepositoryMemory,
)


class MockRoomRepository:
    def find_available(self, *args, **kwargs):
        from app.domain.entities.room.room import Room
        return [
            Room("101", "SINGLE", 100.0, 1, "AVAILABLE"),
        ]

    def get_by_number(self, room_number: str):
        from app.domain.entities.room.room import Room
        return Room(room_number, "SINGLE", 100.0, 1, "AVAILABLE")

    def is_available(self, *args, **kwargs):
        return True


class MockHotelRepositoryAllowsWithout:
    """Hotel que permite reserva sem pagamento (default)."""

    def get_active_hotel(self):
        from app.domain.entities.hotel.hotel import Hotel
        from app.domain.entities.hotel.policies import HotelPolicies
        return Hotel(
            "1", "Hotel", "Addr", "+5561", HotelPolicies("14:00", "12:00", "", "", "", ""),
            requires_payment_for_confirmation=False,
            allows_reservation_without_payment=True,
        )


class MockHotelRepositoryRequiresPayment:
    """Hotel que exige pagamento para confirmação."""

    def get_active_hotel(self):
        from app.domain.entities.hotel.hotel import Hotel
        from app.domain.entities.hotel.policies import HotelPolicies
        return Hotel(
            "1", "Hotel", "Addr", "+5561", HotelPolicies("14:00", "12:00", "", "", "", ""),
            requires_payment_for_confirmation=True,
            allows_reservation_without_payment=False,
        )


def _make_orchestrator(hotel_repo):
    from app.application.use_cases.cancel_reservation import CancelReservationUseCase
    from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
    from app.application.use_cases.create_reservation import CreateReservationUseCase
    from app.application.use_cases.checkout_via_whatsapp import CheckoutViaWhatsAppUseCase
    from app.application.use_cases.confirm_reservation import ConfirmReservationUseCase
    from app.application.use_cases.extend_reservation import ExtendReservationUseCase

    class InMemoryCache:
        def __init__(self):
            self._store = {}
        def get(self, k): return self._store.get(k)
        def set(self, k, v, ttl_seconds=None): self._store[k] = v
        def delete(self, k): self._store.pop(k, None)

    class DummyConversation:
        def execute(self, phone, text): return "fallback"

    reservation_repo = ReservationRepositoryMemory()
    room_repo = MockRoomRepository()
    cache = InMemoryCache()

    create_uc = CreateReservationUseCase(reservation_repo, room_repo)
    confirm_uc = ConfirmReservationUseCase(reservation_repo)
    extend_uc = ExtendReservationUseCase(reservation_repo, room_repo)

    from app.infrastructure.payment.manual_payment_provider import ManualPaymentProvider
    from app.infrastructure.persistence.memory.payment_repository_memory import PaymentRepositoryMemory

    return HandleWhatsAppMessageUseCase(
        checkin_use_case=CheckInViaWhatsAppUseCase(reservation_repo, cache),
        checkout_use_case=CheckoutViaWhatsAppUseCase(reservation_repo),
        cancel_reservation_use_case=CancelReservationUseCase(reservation_repo),
        create_reservation_use_case=create_uc,
        conversation_use_case=DummyConversation(),
        confirm_reservation_use_case=confirm_uc,
        extend_reservation_use_case=extend_uc,
        reservation_repository=reservation_repo,
        cache_repository=cache,
        room_repository=room_repo,
        hotel_repository=hotel_repo,
        payment_provider=ManualPaymentProvider(),
        payment_repository=PaymentRepositoryMemory(),
    )


def test_requires_payment_shows_only_payment_instructions():
    """Quando requires_payment_for_confirmation=True, não oferece opção 2."""
    orch = _make_orchestrator(MockHotelRepositoryRequiresPayment())
    phone = "5561999999999"

    orch.execute(WhatsAppMessageRequestDTO(phone=phone, message="quero fazer reserva", source="twilio"))
    start = date.today() + timedelta(days=10)
    end = date.today() + timedelta(days=12)
    orch.execute(WhatsAppMessageRequestDTO(phone=phone, message=f"{start.strftime('%d/%m/%Y')} e {end.strftime('%d/%m/%Y')}", source="twilio"))
    orch.execute(WhatsAppMessageRequestDTO(phone=phone, message="101", source="twilio"))
    r = orch.execute(WhatsAppMessageRequestDTO(phone=phone, message="João", source="twilio"))

    assert "efetue o pagamento" in r.reply.lower() or "pagamento" in r.reply.lower()
    assert "Confirmar sem pagamento" not in r.reply
    assert "opção 2" not in r.reply.lower() and "opcao 2" not in r.reply.lower()


def test_allows_without_shows_both_options():
    """Quando allows_reservation_without_payment=True, oferece opções 1 e 2."""
    orch = _make_orchestrator(MockHotelRepositoryAllowsWithout())
    phone = "5561888888888"

    orch.execute(WhatsAppMessageRequestDTO(phone=phone, message="quero fazer reserva", source="twilio"))
    start = date.today() + timedelta(days=15)
    end = date.today() + timedelta(days=17)
    orch.execute(WhatsAppMessageRequestDTO(phone=phone, message=f"{start.strftime('%d/%m/%Y')} e {end.strftime('%d/%m/%Y')}", source="twilio"))
    orch.execute(WhatsAppMessageRequestDTO(phone=phone, message="101", source="twilio"))
    r = orch.execute(WhatsAppMessageRequestDTO(phone=phone, message="Maria", source="twilio"))

    assert "1" in r.reply and "2" in r.reply
    assert "Confirmar sem pagamento" in r.reply
