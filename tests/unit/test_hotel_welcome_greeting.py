import pytest

from app.application.dto.whatsapp_message_request_dto import WhatsAppMessageRequestDTO
from app.application.use_cases.handle_whatsapp_message import HandleWhatsAppMessageUseCase


class DummyCacheRepository:
    def __init__(self):
        self.store: dict[str, object] = {}

    def _conversation_key(self, hotel_id: str, phone: str) -> str:
        return f"conversation:{hotel_id}:{phone}"

    def get(self, key_or_hotel_id: str, phone: str | None = None):
        if phone is None:
            return self.store.get(key_or_hotel_id)
        return self.store.get(self._conversation_key(key_or_hotel_id, phone))

    def set(self, key_or_hotel_id: str, value_or_phone, value=None, ttl_seconds: int = 3600):
        if value is None:
            # key-only usage (flow state).
            self.store[key_or_hotel_id] = value_or_phone
            return
        # (hotel_id, phone) usage (conversation history).
        self.store[self._conversation_key(key_or_hotel_id, str(value_or_phone))] = value

    def delete(self, key: str):
        self.store.pop(key, None)


class DummyHotel:
    def __init__(self, name: str, contact_phone: str | None = None):
        self.name = name
        self.contact_phone = contact_phone


class DummyHotelRepository:
    def __init__(self, hotel_name: str):
        self._hotel = DummyHotel(hotel_name)

    def get_active_hotel(self, hotel_id=None):
        return self._hotel


class DummyConversationUseCase:
    def __init__(self):
        self.called = False
        self.response = "IA_OK"

    def execute(self, hotel_id: str, phone: str, text: str) -> str:
        self.called = True
        return self.response


class _NullUseCase:
    def __getattr__(self, name):
        raise AssertionError(f"Unexpected use of dependency: {name}")


def _build_use_case(conversation_called_response: str = "IA_OK", history: list | None = None):
    cache_repo = DummyCacheRepository()
    if history is not None:
        cache_repo.store["conversation:hotel-1:556199999999"] = history

    hotel_repo = DummyHotelRepository("Hotel Tal")
    conversation_uc = DummyConversationUseCase()
    conversation_uc.response = conversation_called_response

    # Dependencies not used by the greeting path can be null objects.
    return (
        HandleWhatsAppMessageUseCase(
            checkin_use_case=_NullUseCase(),
            checkout_use_case=_NullUseCase(),
            cancel_reservation_use_case=_NullUseCase(),
            create_reservation_use_case=_NullUseCase(),
            conversation_use_case=conversation_uc,
            confirm_reservation_use_case=_NullUseCase(),
            extend_reservation_use_case=_NullUseCase(),
            reservation_repository=_NullUseCase(),
            cache_repository=cache_repo,
            room_repository=_NullUseCase(),
            hotel_repository=hotel_repo,
            payment_provider=_NullUseCase(),
            payment_repository=_NullUseCase(),
        ),
        conversation_uc,
    )


def test_welcome_greeting_first_contact_uses_hotel_name_without_human_fallback():
    orch, conversation_uc = _build_use_case(history=None)

    resp = orch.execute(
        hotel_id="hotel-1",
        request_dto=WhatsAppMessageRequestDTO(
            phone="556199999999",
            message="Boa tarde",
            source="twilio",
            has_media=False,
        ),
    )

    assert conversation_uc.called is False
    assert "Boa tarde" in resp.reply
    assert "Hotel Tal" in resp.reply
    assert "Como posso ajudar" in resp.reply
    assert "Hotel Hotel" not in resp.reply
    assert "ATENDENTE" not in resp.reply


def test_welcome_greeting_with_history_uses_ai_without_human_fallback():
    orch, conversation_uc = _build_use_case(history=[{"role": "user", "content": "x"}])
    conversation_uc.response = "IA_OK"

    resp = orch.execute(
        hotel_id="hotel-1",
        request_dto=WhatsAppMessageRequestDTO(
            phone="556199999999",
            message="Boa tarde",
            source="twilio",
            has_media=False,
        ),
    )

    assert conversation_uc.called is True
    assert resp.reply == "IA_OK"
    assert "ATENDENTE" not in resp.reply

