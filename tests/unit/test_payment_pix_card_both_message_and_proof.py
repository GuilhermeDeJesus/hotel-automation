import types
from datetime import date, timedelta

from app.application.dto.whatsapp_message_request_dto import WhatsAppMessageRequestDTO
from app.application.use_cases.handle_whatsapp_message import HandleWhatsAppMessageUseCase
from app.domain.entities.payment.payment import Payment
from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.entities.reservation.stay_period import StayPeriod
from app.domain.value_objects.phone_number import PhoneNumber


class CacheRepoStub:
    def __init__(self):
        self._store = {}

    def get(self, key: str):
        return self._store.get(key)

    def set(self, key: str, value, ttl_seconds: int = 900):
        self._store[key] = value

    def delete(self, key: str):
        self._store.pop(key, None)


class ReservationRepoStub:
    def __init__(self, reservation: Reservation | None):
        self._reservation = reservation

    def find_by_phone_number(self, phone: str, hotel_id: str):
        return self._reservation

    def find_by_id(self, reservation_id: str, hotel_id: str):
        return self._reservation


class PaymentRepoStub:
    def __init__(self):
        self.saved = []

    def save(self, hotel_id: str, payment: Payment):
        self.saved.append((hotel_id, payment))


def _build_use_case(cache_repo: CacheRepoStub, reservation_repo, payment_repo, hotel_repo, payment_provider) -> HandleWhatsAppMessageUseCase:
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
        reservation_repository=reservation_repo,
        cache_repository=cache_repo,
        room_repository=dummy,
        hotel_repository=hotel_repo,
        payment_provider=payment_provider,
        payment_repository=payment_repo,
    )


def test_payment_message_includes_pix_and_card_link_when_stripe_available():
    cache = CacheRepoStub()
    payment_repo = PaymentRepoStub()

    hotel_id = "hotel-1"
    phone = "5561999999999"
    pix_key = "chavepix@hotel.com"

    hotel_repo = types.SimpleNamespace(
        get_active_hotel=lambda hid=None: types.SimpleNamespace(
            contact_phone="outro@contato.com",
            pix_key=pix_key,
        )
    )

    payment_provider = types.SimpleNamespace(
        create_checkout_link=lambda *args, **kwargs: ("https://stripe.test/checkout", "sess_1")
    )

    reservation = Reservation(
        reservation_id="res-1",
        guest_name="Guilherme",
        hotel_id=hotel_id,
        guest_phone=PhoneNumber(phone),
        status=ReservationStatus.PENDING,
        stay_period=StayPeriod(date.today() + timedelta(days=7), date.today() + timedelta(days=9)),
        room_number="504",
        total_amount=250.0,
    )
    reservation_repo = ReservationRepoStub(reservation)

    use_case = _build_use_case(
        cache_repo=cache,
        reservation_repo=reservation_repo,
        payment_repo=payment_repo,
        hotel_repo=hotel_repo,
        payment_provider=payment_provider,
    )

    flow_state = {
        "action": use_case.CREATE_RESERVATION_ACTION,
        "step": use_case.STEP_AWAITING_CHILDREN,
        "guest_name": "Guilherme",
        "reservation_id": "res-1",
        "selected_room": "504",
        "room_type": "DOUBLE",
        "check_in": (date.today() + timedelta(days=7)).isoformat(),
        "check_out": (date.today() + timedelta(days=9)).isoformat(),
        "total_amount": 250.0,
        "num_guests": 2,
        "num_children": 0,
        "has_children": False,
        "requires_payment": True,
        "allows_without": True,
    }
    use_case._set_flow_state(f"{hotel_id}:{phone}", flow_state)

    resp = use_case.execute(
        hotel_id=hotel_id,
        request_dto=WhatsAppMessageRequestDTO(phone=phone, message="nao", source="meta"),
    )

    assert resp.success is True
    assert "chave pix" in resp.reply.lower()
    assert pix_key in resp.reply
    assert "outro@contato.com" not in resp.reply
    assert "stripe.test/checkout" in resp.reply
    assert len(payment_repo.saved) == 1


def test_payment_proof_media_without_flow_state_creates_manual_payment():
    cache = CacheRepoStub()
    payment_repo = PaymentRepoStub()

    hotel_id = "hotel-1"
    phone = "5561999999999"

    reservation = Reservation(
        reservation_id="res-1",
        guest_name="Guilherme",
        hotel_id=hotel_id,
        guest_phone=PhoneNumber(phone),
        status=ReservationStatus.PENDING,
        stay_period=StayPeriod(date.today() + timedelta(days=7), date.today() + timedelta(days=9)),
        room_number="504",
        total_amount=250.0,
    )
    reservation_repo = ReservationRepoStub(reservation)

    hotel_repo = types.SimpleNamespace(
        get_active_hotel=lambda hid=None: types.SimpleNamespace(contact_phone="chavepix@hotel.com")
    )
    payment_provider = types.SimpleNamespace(
        create_checkout_link=lambda *args, **kwargs: None
    )

    use_case = _build_use_case(
        cache_repo=cache,
        reservation_repo=reservation_repo,
        payment_repo=payment_repo,
        hotel_repo=hotel_repo,
        payment_provider=payment_provider,
    )

    resp = use_case.execute(
        hotel_id=hotel_id,
        request_dto=WhatsAppMessageRequestDTO(
            phone=phone,
            message="",
            source="twilio",
            has_media=True,
        ),
    )

    assert resp.success is True
    assert "Recebemos seu comprovante" in resp.reply
    assert len(payment_repo.saved) == 1
    saved_hotel_id, payment = payment_repo.saved[0]
    assert saved_hotel_id == hotel_id
    assert payment.payment_method == "manual"

