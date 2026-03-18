import types

from app.application.dto.whatsapp_message_request_dto import WhatsAppMessageRequestDTO
from app.application.use_cases.handle_whatsapp_message import HandleWhatsAppMessageUseCase


class CacheRepoStub:
    def __init__(self):
        self._store = {}

    def get(self, key: str):
        return self._store.get(key)

    def set(self, key: str, value, ttl_seconds: int = 900):
        self._store[key] = value

    def delete(self, key: str):
        self._store.pop(key, None)


class HotelRepoStub:
    def get_active_hotel(self, hotel_id=None):
        return types.SimpleNamespace(
            id=hotel_id,
            name="Hotel Teste",
            contact_phone="5511999999999",
        )


def _build_use_case(cache_repo: CacheRepoStub) -> HandleWhatsAppMessageUseCase:
    dummy = types.SimpleNamespace(
        execute=lambda *args, **kwargs: None,
        prepare_cancellation=lambda *args, **kwargs: None,
        cancel=lambda *args, **kwargs: None,
        prepare_confirmation=lambda *args, **kwargs: None,
        get_formatted_summary_for_phone=lambda *args, **kwargs: "",
        confirm=lambda *args, **kwargs: None,
        prepare_extension=lambda *args, **kwargs: None,
        extend=lambda *args, **kwargs: None,
        create=lambda *args, **kwargs: None,
        check_availability=lambda *args, **kwargs: [],
    )

    return HandleWhatsAppMessageUseCase(
        checkin_use_case=dummy,
        checkout_use_case=dummy,
        cancel_reservation_use_case=dummy,
        create_reservation_use_case=dummy,
        conversation_use_case=dummy,
        confirm_reservation_use_case=dummy,
        extend_reservation_use_case=dummy,
        reservation_repository=dummy,
        cache_repository=cache_repo,
        room_repository=dummy,
        hotel_repository=HotelRepoStub(),
        payment_provider=dummy,
        payment_repository=dummy,
    )


def test_hotel_identity_question_returns_hotel_name():
    cache = CacheRepoStub()
    use_case = _build_use_case(cache)

    resp = use_case.execute(
        hotel_id="hotel-1",
        request_dto=WhatsAppMessageRequestDTO(
            phone="5561999999999",
            message="de que hotel estou falando ?",
            source="twilio",
        ),
    )

    assert resp.success is True
    assert "Hotel Teste" in resp.reply
    assert "Contato do hotel" in resp.reply

