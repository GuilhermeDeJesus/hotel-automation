import types
from datetime import date, timedelta

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
        hotel_repository=dummy,
        payment_provider=dummy,
        payment_repository=dummy,
    )


def test_create_reservation_guest_count_moves_to_children_question():
    cache = CacheRepoStub()
    use_case = _build_use_case(cache)

    hotel_id = "hotel-1"
    phone = "5561999999999"

    flow_state = {
        "action": use_case.CREATE_RESERVATION_ACTION,
        "step": use_case.STEP_AWAITING_GUEST_COUNT,
    }
    use_case._set_flow_state(f"{hotel_id}:{phone}", flow_state)

    resp = use_case.execute(
        hotel_id=hotel_id,
        request_dto=WhatsAppMessageRequestDTO(
            phone=phone,
            message="3",
            source="meta",
        ),
    )

    assert resp.success is True
    assert resp.message_type == "button"
    assert "crianças" in resp.reply.lower()
    assert any(btn["id"] == "sim" for btn in resp.buttons)
    assert any(btn["id"] == "nao" for btn in resp.buttons)


def test_create_reservation_children_no_finalizes_payment_choice():
    cache = CacheRepoStub()
    use_case = _build_use_case(cache)

    hotel_id = "hotel-1"
    phone = "5561999999999"

    check_in = date.today() + timedelta(days=7)
    check_out = date.today() + timedelta(days=9)

    flow_state = {
        "action": use_case.CREATE_RESERVATION_ACTION,
        "step": use_case.STEP_AWAITING_CHILDREN,
        "guest_name": "Guilherme",
        "reservation_id": "res-1",
        "selected_room": "504",
        "room_type": "DOUBLE",
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "total_amount": 250.0,
        "num_guests": 3,
        "requires_payment": False,
        "allows_without": True,
    }
    use_case._set_flow_state(f"{hotel_id}:{phone}", flow_state)

    resp = use_case.execute(
        hotel_id=hotel_id,
        request_dto=WhatsAppMessageRequestDTO(
            phone=phone,
            message="nao",
            source="twilio",
        ),
    )

    assert resp.success is True
    assert resp.message_type == "button"
    assert "Como deseja prosseguir" in resp.reply
    assert "Hóspedes: 3" in resp.reply
    assert "Crianças: 0" in resp.reply
    assert any(btn["id"] == "1" for btn in resp.buttons)
    assert any(btn["id"] == "2" for btn in resp.buttons)


def test_create_reservation_children_count_finalizes_payment_choice():
    cache = CacheRepoStub()
    use_case = _build_use_case(cache)

    hotel_id = "hotel-1"
    phone = "5561999999999"

    check_in = date.today() + timedelta(days=7)
    check_out = date.today() + timedelta(days=9)

    flow_state = {
        "action": use_case.CREATE_RESERVATION_ACTION,
        "step": use_case.STEP_AWAITING_CHILDREN_COUNT,
        "guest_name": "Guilherme",
        "reservation_id": "res-1",
        "selected_room": "504",
        "room_type": "DOUBLE",
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "total_amount": 250.0,
        "num_guests": 3,
        "has_children": True,
        "requires_payment": False,
        "allows_without": True,
    }
    use_case._set_flow_state(f"{hotel_id}:{phone}", flow_state)

    resp = use_case.execute(
        hotel_id=hotel_id,
        request_dto=WhatsAppMessageRequestDTO(
            phone=phone,
            message="1",
            source="meta",
        ),
    )

    assert resp.success is True
    assert resp.message_type == "button"
    assert "Crianças: 1" in resp.reply
    assert "Como deseja prosseguir" in resp.reply

