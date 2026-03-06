from app.application.dto.confirm_reservation_response_dto import ConfirmReservationResponseDTO
from app.application.dto.whatsapp_message_request_dto import WhatsAppMessageRequestDTO
from app.application.use_cases.handle_whatsapp_message import HandleWhatsAppMessageUseCase
from app.infrastructure.cache.redis_repository import RedisRepository


class DummyCheckinUseCase:
    def execute(self, request_dto):
        raise AssertionError("Check-in use case should not be called in this test")


class DummyCheckoutUseCase:
    def execute(self, request_dto):
        raise AssertionError("Check-out use case should not be called in this test")


class DummyCancelReservationUseCase:
    def prepare_cancellation(self, request_dto):
        raise AssertionError("Cancel use case should not be called in this test")

    def cancel(self, request_dto):
        raise AssertionError("Cancel use case should not be called in this test")


class DummyCreateReservationUseCase:
    def check_availability(self, *args, **kwargs):
        raise AssertionError("Create reservation use case should not be called in this test")

    def create(self, request_dto):
        raise AssertionError("Create reservation use case should not be called in this test")


class DummyConversationUseCase:
    def execute(self, phone: str, text: str) -> str:
        raise AssertionError("Conversation use case should not be called in this test")


class DummyReservationRepository:
    class DummyReservation:
        pass

    def find_by_phone_number(self, phone: str):
        return self.DummyReservation()


class DummyConfirmReservationUseCase:
    def __init__(self):
        self.reservation_repository = DummyReservationRepository()

    def prepare_confirmation(self, request_dto):
        return ConfirmReservationResponseDTO(
            message="Resumo preparado",
            success=True,
            can_confirm=True,
        )

    def get_formatted_summary_for_phone(self, phone: str) -> str | None:
        return "Resumo da reserva para confirmação"

    def get_formatted_summary(self, reservation):
        return "Resumo da reserva para confirmação"

    def confirm(self, request_dto):
        return ConfirmReservationResponseDTO(
            message="Reserva confirmada com sucesso",
            success=True,
            can_confirm=False,
        )


class DummyRoomRepository:
    def find_available(self, *args, **kwargs):
        return []


class DummyHotelRepository:
    """Retorna None = defaults (oferece ambas opções de pagamento)."""

    def get_active_hotel(self):
        return None


class DummyExtendReservationUseCase:
    def prepare_extension(self, request_dto):
        raise AssertionError("Extend use case should not be called in this test")

    def extend(self, request_dto):
        raise AssertionError("Extend use case should not be called in this test")


def test_confirm_flow_state_ttl_and_cleanup_in_real_redis():
    phone = "559999100002"
    flow_key = f"flow:{phone}"

    cache = RedisRepository()
    cache.delete(flow_key)

    from app.infrastructure.payment.manual_payment_provider import ManualPaymentProvider
    from app.infrastructure.persistence.memory.payment_repository_memory import PaymentRepositoryMemory

    use_case = HandleWhatsAppMessageUseCase(
        checkin_use_case=DummyCheckinUseCase(),
        checkout_use_case=DummyCheckoutUseCase(),
        cancel_reservation_use_case=DummyCancelReservationUseCase(),
        create_reservation_use_case=DummyCreateReservationUseCase(),
        conversation_use_case=DummyConversationUseCase(),
        confirm_reservation_use_case=DummyConfirmReservationUseCase(),
        extend_reservation_use_case=DummyExtendReservationUseCase(),
        reservation_repository=DummyReservationRepository(),
        cache_repository=cache,
        room_repository=DummyRoomRepository(),
        hotel_repository=DummyHotelRepository(),
        payment_provider=ManualPaymentProvider(),
        payment_repository=PaymentRepositoryMemory(),
    )

    start_response = use_case.execute(
        WhatsAppMessageRequestDTO(
            phone=phone,
            message="quero confirmar reserva",
            source="twilio",
        )
    )

    assert start_response.success is True
    assert "SIM / NÃO / EDITAR" in start_response.reply

    flow_state = cache.get(flow_key)
    assert flow_state is not None
    assert flow_state["action"] == "confirm_reservation"
    assert flow_state["step"] == "summary_displayed"

    ttl = cache.client.ttl(flow_key)
    assert 0 < ttl <= 900

    confirm_response = use_case.execute(
        WhatsAppMessageRequestDTO(phone=phone, message="SIM", source="twilio")
    )

    assert confirm_response.success is True
    assert "Reserva confirmada com sucesso" in confirm_response.reply

    assert cache.get(flow_key) is None
    assert cache.exists(flow_key) is False
