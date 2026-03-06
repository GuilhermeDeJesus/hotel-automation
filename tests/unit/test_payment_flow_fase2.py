"""Testes unitários do fluxo de pagamento Fase 2 (Payment + webhook)."""
from datetime import date, timedelta
from unittest.mock import MagicMock

from app.application.use_cases.handle_whatsapp_message import HandleWhatsAppMessageUseCase
from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
from app.application.use_cases.checkout_via_whatsapp import CheckoutViaWhatsAppUseCase
from app.application.use_cases.cancel_reservation import CancelReservationUseCase
from app.application.use_cases.create_reservation import CreateReservationUseCase
from app.application.use_cases.confirm_reservation import ConfirmReservationUseCase
from app.application.use_cases.extend_reservation import ExtendReservationUseCase
from app.application.dto.whatsapp_message_request_dto import WhatsAppMessageRequestDTO
from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.value_objects.phone_number import PhoneNumber
from app.domain.entities.reservation.stay_period import StayPeriod
from app.infrastructure.persistence.memory.reservation_repository_memory import ReservationRepositoryMemory
from app.infrastructure.persistence.memory.payment_repository_memory import PaymentRepositoryMemory


class MockStripePaymentProvider:
    """Provider que retorna (url, session_id) para simular Fase 2."""

    def create_checkout_link(
        self,
        reservation_id: str,
        amount_cents: int,
        description: str,
        currency: str = "brl",
        payment_id: str | None = None,
    ):
        return ("https://checkout.stripe.com/pay/cs_test_123", "cs_test_123")


class MockRoomRepository:
    def find_available(self, check_in, check_out):
        return [
            type("Room", (), {"number": "101", "room_type": "SINGLE", "daily_rate": 150.0})(),
        ]

    def get_by_number(self, number):
        return type("Room", (), {"number": number, "room_type": "SINGLE", "daily_rate": 150.0})()


class MockHotelRepository:
    def get_active_hotel(self):
        return None


def test_pagar_agora_cria_payment_e_retorna_link():
    """
    Quando usuário escolhe pagar agora com Stripe, cria Payment e retorna link.
    """
    reservation_repo = ReservationRepositoryMemory()
    payment_repo = PaymentRepositoryMemory()

    start = date.today() + timedelta(days=10)
    end = date.today() + timedelta(days=12)
    reservation = Reservation(
        reservation_id="res-1",
        guest_name="Maria",
        guest_phone=PhoneNumber("5561888888888"),
        status=ReservationStatus.PENDING,
        stay_period=StayPeriod(start, end, allow_past=True),
        room_number="101",
        total_amount=300.0,
    )
    reservation_repo.save(reservation)

    class InMemoryCache:
        def __init__(self):
            self.store = {}

        def get(self, key):
            return self.store.get(key)

        def set(self, key, value, ttl_seconds=900):
            self.store[key] = value

        def delete(self, key):
            self.store.pop(key, None)

        def exists(self, key):
            return key in self.store

    cache = InMemoryCache()
    cache.set(
        "flow:5561888888888",
        {
            "action": "create_reservation",
            "step": "awaiting_payment_choice",
            "reservation_id": "res-1",
            "guest_name": "Maria",
            "selected_room": "101",
            "check_in": start.isoformat(),
            "check_out": end.isoformat(),
            "available_rooms": [{"number": "101", "room_type": "SINGLE", "daily_rate": 150.0}],
        },
        900,
    )

    class DummyConversation:
        def execute(self, phone, text):
            return "fallback"

    use_case = HandleWhatsAppMessageUseCase(
        checkin_use_case=CheckInViaWhatsAppUseCase(reservation_repo, cache),
        checkout_use_case=CheckoutViaWhatsAppUseCase(reservation_repo),
        cancel_reservation_use_case=CancelReservationUseCase(reservation_repo),
        create_reservation_use_case=CreateReservationUseCase(reservation_repo, MockRoomRepository()),
        conversation_use_case=DummyConversation(),
        confirm_reservation_use_case=ConfirmReservationUseCase(reservation_repo),
        extend_reservation_use_case=ExtendReservationUseCase(reservation_repo, MockRoomRepository()),
        reservation_repository=reservation_repo,
        cache_repository=cache,
        room_repository=MockRoomRepository(),
        hotel_repository=MockHotelRepository(),
        payment_provider=MockStripePaymentProvider(),
        payment_repository=payment_repo,
    )

    response = use_case.execute(
        WhatsAppMessageRequestDTO(phone="5561888888888", message="1", source="twilio")
    )

    assert response.success is True
    assert "checkout.stripe.com" in response.reply or "https://" in response.reply

    payments = list(payment_repo._payments.values())
    assert len(payments) == 1
    assert payments[0].reservation_id == "res-1"
    assert payments[0].amount == 300.0
    assert payments[0].status == "PENDING"
    assert payments[0].transaction_id == "cs_test_123"
