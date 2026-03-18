import types

from app.application.use_cases.handle_whatsapp_message import HandleWhatsAppMessageUseCase
from app.application.dto.whatsapp_message_request_dto import WhatsAppMessageRequestDTO


class CacheRepoStub:
    def __init__(self):
        self._store = {}

    def get(self, key: str):
        return self._store.get(key)

    def set(self, key: str, value, ttl_seconds: int = 900):
        self._store[key] = value

    def delete(self, key: str):
        self._store.pop(key, None)


def _build_use_case(cache_repo: CacheRepoStub) -> HandleWhatsAppMessageUseCase:
    # Para este teste, a recuperação deve acontecer antes de qualquer dependência de domínio
    # além do cache_repository.
    dummy = types.SimpleNamespace(
        execute=lambda *args, **kwargs: None,
        prepare_cancellation=lambda *args, **kwargs: None,
        cancel=lambda *args, **kwargs: None,
        prepare_confirmation=lambda *args, **kwargs: None,
        get_formatted_summary_for_phone=lambda *args, **kwargs: "",
        confirm=lambda *args, **kwargs: None,
        prepare_extension=lambda *args, **kwargs: None,
        extend=lambda *args, **kwargs: None,
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
        hotel_repository=dummy,
        payment_provider=dummy,
        payment_repository=dummy,
    )


def test_context_lost_when_flow_missing_but_user_sends_flow_answer():
    cache = CacheRepoStub()
    use_case = _build_use_case(cache)

    # "sim" é heurística de continuidade do fluxo.
    resp = use_case.execute(
        hotel_id="hotel-1",
        request_dto=WhatsAppMessageRequestDTO(
            phone="5561999999999",
            message="sim",
            source="meta",
        ),
    )

    assert resp.success is True
    assert "Perdi seu contexto" in resp.reply
    assert resp.message_type == "button"
    assert any(btn["id"] == "reserva" for btn in resp.buttons)
    assert any(btn["id"] == "cancelar" for btn in resp.buttons)


def test_is_cancel_intent_accepts_cancelar_word():
    cache = CacheRepoStub()
    use_case = _build_use_case(cache)

    assert use_case._is_cancel_reservation_intent("cancelar") is True
    assert use_case._is_cancel_reservation_intent("cancelar!") is False

