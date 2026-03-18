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

    def exists(self, key: str) -> bool:
        return key in self._store


class ReservationRepoStub:
    def __init__(self, room_number: str | None = None):
        self._room_number = room_number

    def find_by_phone_number(self, phone_number: str, hotel_id: str):
        return types.SimpleNamespace(room_number=self._room_number)


class HotelMediaRepoStub:
    def __init__(self, mapping: dict[tuple[str, str | None], list[str]]):
        self.mapping = mapping
        self.calls = []

    def get_media_set_photo_ids(self, hotel_id: str, scope: str, room_number: str | None = None, limit: int = 3):
        self.calls.append((hotel_id, scope, room_number, limit))
        return self.mapping.get((scope, room_number), [])


def _dummy_use_case(
    cache_repo: CacheRepoStub,
    hotel_media_repo: HotelMediaRepoStub,
) -> HandleWhatsAppMessageUseCase:
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

    # conversation_use_case só será usada como fallback quando não houver hotel_media_repo.
    conversation_dummy = types.SimpleNamespace(
        execute=lambda *args, **kwargs: "fallback",
    )

    return HandleWhatsAppMessageUseCase(
        checkin_use_case=dummy,
        checkout_use_case=dummy,
        cancel_reservation_use_case=dummy,
        create_reservation_use_case=dummy,
        conversation_use_case=conversation_dummy,
        confirm_reservation_use_case=dummy,
        extend_reservation_use_case=dummy,
        reservation_repository=ReservationRepoStub(room_number="101"),
        cache_repository=cache_repo,
        room_repository=dummy,
        hotel_repository=dummy,
        payment_provider=dummy,
        payment_repository=dummy,
        hotel_media_repository=hotel_media_repo,
    )


def test_photo_request_sends_photo_set_and_stores_flow_state():
    cache = CacheRepoStub()
    hotel_media_repo = HotelMediaRepoStub(
        mapping={
            ("ROOM", "101"): ["r1", "r2", "r3"],
        }
    )
    use_case = _dummy_use_case(cache, hotel_media_repo)

    resp = use_case.execute(
        hotel_id="hotel-1",
        request_dto=WhatsAppMessageRequestDTO(
            phone="5561999999999",
            message="quero ver fotos do quarto",
            source="twilio",
        ),
    )

    assert resp.success is True
    assert resp.message_type == "photo_set"
    assert resp.media_ids == ["r1", "r2", "r3"]
    assert len(resp.buttons) == 3

    # garante que pediu exatamente uma seleção de 3 fotos
    assert hotel_media_repo.calls == [("hotel-1", "ROOM", "101", 3)]

    # flow state deve ter sido salvo
    flow_key = f"flow:{'hotel-1'}:{'5561999999999'}"
    assert cache.get(flow_key) is not None


def test_photo_choice_flow_sends_single_photo_and_clears_flow_state():
    cache = CacheRepoStub()
    hotel_media_repo = HotelMediaRepoStub(
        mapping={
            ("ROOM", "101"): ["r1", "r2", "r3"],
        }
    )
    use_case = _dummy_use_case(cache, hotel_media_repo)

    hotel_id = "hotel-1"
    phone = "5561999999999"

    # start flow
    use_case.execute(
        hotel_id=hotel_id,
        request_dto=WhatsAppMessageRequestDTO(
            phone=phone,
            message="quero ver fotos do quarto",
            source="twilio",
        ),
    )

    flow_key = f"flow:{hotel_id}:{phone}"
    assert cache.get(flow_key) is not None

    # choose "2"
    resp = use_case.execute(
        hotel_id=hotel_id,
        request_dto=WhatsAppMessageRequestDTO(
            phone=phone,
            message="2",
            source="twilio",
        ),
    )

    assert resp.success is True
    assert resp.message_type == "photo"
    assert resp.media_ids == ["r2"]
    assert resp.media_caption == "Foto 2"

    # flow state deve ter sido limpo
    assert cache.get(flow_key) is None

