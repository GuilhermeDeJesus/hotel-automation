from datetime import date, timedelta
from uuid import uuid4

from app.application.dto.whatsapp_message_request_dto import WhatsAppMessageRequestDTO
from app.application.use_cases.cancel_reservation import CancelReservationUseCase
from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
from app.application.use_cases.create_reservation import CreateReservationUseCase
from app.application.use_cases.checkout_via_whatsapp import CheckoutViaWhatsAppUseCase
from app.application.use_cases.confirm_reservation import ConfirmReservationUseCase
from app.application.use_cases.extend_reservation import ExtendReservationUseCase
from app.application.use_cases.handle_whatsapp_message import HandleWhatsAppMessageUseCase
from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.entities.reservation.stay_period import StayPeriod
from app.domain.value_objects.phone_number import PhoneNumber
from app.infrastructure.cache.redis_repository import RedisRepository
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.room_repository_sql import RoomRepositorySQL
from app.infrastructure.persistence.sql.reservation_repository_sql import ReservationRepositorySQL
from app.infrastructure.persistence.sql.hotel_repository_sql import HotelRepositorySQL


class DummyConversationUseCase:
    def execute(self, phone: str, text: str) -> str:
        return "fallback"


def _unique_phone() -> str:
    return "55999" + str(uuid4().int)[0:8]


def _build_orchestrator(
    cache: RedisRepository,
    reservation_repo: ReservationRepositorySQL,
    room_repo: RoomRepositorySQL,
    hotel_repo: HotelRepositorySQL | None = None,
) -> HandleWhatsAppMessageUseCase:
    checkin_use_case = CheckInViaWhatsAppUseCase(
        reservation_repository=reservation_repo,
        cache_repository=cache,
    )
    checkout_use_case = CheckoutViaWhatsAppUseCase(reservation_repository=reservation_repo)
    cancel_reservation_use_case = CancelReservationUseCase(reservation_repository=reservation_repo)
    create_reservation_use_case = CreateReservationUseCase(
        reservation_repository=reservation_repo,
        room_repository=room_repo,
    )
    confirm_use_case = ConfirmReservationUseCase(reservation_repository=reservation_repo)
    extend_use_case = ExtendReservationUseCase(
        reservation_repository=reservation_repo,
        room_repository=room_repo,
    )
    if hotel_repo is None:
        hotel_repo = HotelRepositorySQL(reservation_repo.session)

    from app.infrastructure.payment.manual_payment_provider import ManualPaymentProvider
    from app.infrastructure.persistence.sql.payment_repository_sql import PaymentRepositorySQL

    return HandleWhatsAppMessageUseCase(
        checkin_use_case=checkin_use_case,
        checkout_use_case=checkout_use_case,
        cancel_reservation_use_case=cancel_reservation_use_case,
        create_reservation_use_case=create_reservation_use_case,
        conversation_use_case=DummyConversationUseCase(),
        confirm_reservation_use_case=confirm_use_case,
        extend_reservation_use_case=extend_use_case,
        reservation_repository=reservation_repo,
        cache_repository=cache,
        room_repository=room_repo,
        hotel_repository=hotel_repo,
        payment_provider=ManualPaymentProvider(),
        payment_repository=PaymentRepositorySQL(reservation_repo.session),
    )


def test_business_checkin_updates_postgres_and_redis():
    session = SessionLocal()
    repo = ReservationRepositorySQL(session)
    room_repo = RoomRepositorySQL(session)
    cache = RedisRepository()

    phone = _unique_phone()
    checkin_done_key = f"{CheckInViaWhatsAppUseCase.CHECKIN_DONE_KEY_PREFIX}{phone}"
    cache.delete(checkin_done_key)

    reservation = Reservation(
        reservation_id="",
        guest_name="Hospede Checkin",
        guest_phone=PhoneNumber(phone),
        status=ReservationStatus.PENDING,
        stay_period=StayPeriod(date.today(), date.today() + timedelta(days=1)),
        room_number="101",
        total_amount=250.0,
    )
    repo.save(reservation)

    orchestrator = _build_orchestrator(cache, repo, room_repo)

    response = orchestrator.execute(
        WhatsAppMessageRequestDTO(phone=phone, message="checkin", source="twilio")
    )

    assert response.success is True
    assert "Check-in feito com sucesso" in response.reply

    persisted = repo.find_by_phone_number(phone)
    assert persisted is not None
    assert persisted.status == ReservationStatus.CHECKED_IN

    cached = cache.get(checkin_done_key)
    assert cached is not None
    assert cached.get("done") is True

    session.close()


def test_business_confirm_flow_updates_postgres_and_cleans_flow_key():
    session = SessionLocal()
    repo = ReservationRepositorySQL(session)
    room_repo = RoomRepositorySQL(session)
    cache = RedisRepository()

    phone = _unique_phone()
    flow_key = f"flow:{phone}"
    cache.delete(flow_key)

    reservation = Reservation(
        reservation_id="",
        guest_name="Hospede Confirmacao",
        guest_phone=PhoneNumber(phone),
        status=ReservationStatus.PENDING,
        stay_period=StayPeriod(date.today(), date.today() + timedelta(days=2)),
        room_number="102",
        total_amount=600.0,
    )
    repo.save(reservation)

    orchestrator = _build_orchestrator(cache, repo, room_repo)

    start_response = orchestrator.execute(
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

    confirm_response = orchestrator.execute(
        WhatsAppMessageRequestDTO(phone=phone, message="SIM", source="twilio")
    )

    assert confirm_response.success is True
    assert "Reserva confirmada com sucesso" in confirm_response.reply

    persisted = repo.find_by_phone_number(phone)
    assert persisted is not None
    assert persisted.status == ReservationStatus.CONFIRMED

    assert cache.get(flow_key) is None
    assert cache.exists(flow_key) is False

    session.close()


def test_business_checkout_updates_postgres():
    session = SessionLocal()
    repo = ReservationRepositorySQL(session)
    room_repo = RoomRepositorySQL(session)
    cache = RedisRepository()

    phone = _unique_phone()
    checkin_done_key = f"{CheckInViaWhatsAppUseCase.CHECKIN_DONE_KEY_PREFIX}{phone}"
    cache.delete(checkin_done_key)

    reservation = Reservation(
        reservation_id="",
        guest_name="Hospede Checkout",
        guest_phone=PhoneNumber(phone),
        status=ReservationStatus.CHECKED_IN,
        stay_period=StayPeriod(date.today(), date.today() + timedelta(days=1)),
        room_number="101",
        total_amount=250.0,
    )
    repo.save(reservation)

    orchestrator = _build_orchestrator(cache, repo, room_repo)

    response = orchestrator.execute(
        WhatsAppMessageRequestDTO(phone=phone, message="checkout", source="twilio")
    )

    assert response.success is True
    assert "Check-out realizado com sucesso" in response.reply

    persisted = repo.find_by_phone_number(phone)
    assert persisted is not None
    assert persisted.status == ReservationStatus.CHECKED_OUT

    session.close()


def test_business_cancel_flow_updates_postgres():
    session = SessionLocal()
    repo = ReservationRepositorySQL(session)
    room_repo = RoomRepositorySQL(session)
    cache = RedisRepository()

    phone = _unique_phone()
    flow_key = f"flow:{phone}"
    cache.delete(flow_key)

    reservation = Reservation(
        reservation_id="",
        guest_name="Hospede Cancelamento",
        guest_phone=PhoneNumber(phone),
        status=ReservationStatus.PENDING,
        stay_period=StayPeriod(date.today(), date.today() + timedelta(days=2)),
        room_number="103",
        total_amount=500.0,
    )
    repo.save(reservation)

    orchestrator = _build_orchestrator(cache, repo, room_repo)

    start_response = orchestrator.execute(
        WhatsAppMessageRequestDTO(
            phone=phone,
            message="quero cancelar reserva",
            source="twilio",
        )
    )

    assert start_response.success is True
    assert "SIM" in start_response.reply or "NÃO" in start_response.reply

    flow_state = cache.get(flow_key)
    assert flow_state is not None
    assert flow_state["action"] == "cancel_reservation"

    # Usuário confirma cancelamento
    cancel_response = orchestrator.execute(
        WhatsAppMessageRequestDTO(phone=phone, message="SIM", source="twilio")
    )

    assert cancel_response.success is True
    assert "Reserva cancelada com sucesso" in cancel_response.reply

    persisted = repo.find_by_phone_number(phone)
    assert persisted is not None
    assert persisted.status == ReservationStatus.CANCELLED

    assert cache.get(flow_key) is None

    session.close()


def test_business_create_reservation_flow_persists_in_postgres():
    """Fluxo guiado: fazer reserva -> datas -> quarto -> nome -> confirma -> persiste."""
    session = SessionLocal()
    repo = ReservationRepositorySQL(session)
    room_repo = RoomRepositorySQL(session)
    cache = RedisRepository()

    phone = _unique_phone()
    flow_key = f"flow:{phone}"
    cache.delete(flow_key)

    orchestrator = _build_orchestrator(cache, repo, room_repo)

    # 1. Inicia fluxo
    r1 = orchestrator.execute(
        WhatsAppMessageRequestDTO(
            phone=phone,
            message="quero fazer reserva",
            source="twilio",
        )
    )
    assert r1.success is True
    assert "datas" in r1.reply.lower()

    # 2. Envia datas (formato DD/MM/YYYY)
    start = date.today() + timedelta(days=14)
    end = date.today() + timedelta(days=16)
    dates_msg = f"{start.strftime('%d/%m/%Y')} e {end.strftime('%d/%m/%Y')}"
    r2 = orchestrator.execute(
        WhatsAppMessageRequestDTO(phone=phone, message=dates_msg, source="twilio")
    )
    assert r2.success is True
    assert "101" in r2.reply or "102" in r2.reply or "201" in r2.reply

    # 3. Escolhe quarto (usa primeiro disponível: 102 ou 201)
    first_room = "102" if "102" in r2.reply else "201"
    r3 = orchestrator.execute(
        WhatsAppMessageRequestDTO(phone=phone, message=first_room, source="twilio")
    )
    assert r3.success is True
    assert "nome" in r3.reply.lower()

    # 4. Envia nome (cria reserva PENDING e mostra opções de pagamento)
    r4 = orchestrator.execute(
        WhatsAppMessageRequestDTO(phone=phone, message="João Silva", source="twilio")
    )
    assert r4.success is True
    assert "1" in r4.reply and "2" in r4.reply
    assert "pagamento" in r4.reply.lower()

    # 5. Escolhe confirmar sem pagamento (Passo 10 - Fase 0)
    r5 = orchestrator.execute(
        WhatsAppMessageRequestDTO(phone=phone, message="2", source="twilio")
    )
    assert r5.success is True
    assert "confirmada" in r5.reply.lower()

    persisted = repo.find_by_phone_number(phone)
    assert persisted is not None
    assert persisted.status == ReservationStatus.CONFIRMED
    assert persisted.room_number == first_room
    assert persisted.guest_name == "João Silva"
    assert persisted.total_amount > 0

    assert cache.get(flow_key) is None

    session.close()


def test_business_create_reservation_pay_now_keeps_pending():
    """Fluxo: fazer reserva -> datas -> quarto -> nome -> pagar agora -> reserva PENDING."""
    session = SessionLocal()
    repo = ReservationRepositorySQL(session)
    room_repo = RoomRepositorySQL(session)
    cache = RedisRepository()

    phone = _unique_phone()
    flow_key = f"flow:{phone}"
    cache.delete(flow_key)

    orchestrator = _build_orchestrator(cache, repo, room_repo)

    # 1-3: datas, quarto
    orchestrator.execute(
        WhatsAppMessageRequestDTO(phone=phone, message="quero fazer reserva", source="twilio")
    )
    start = date.today() + timedelta(days=20)
    end = date.today() + timedelta(days=22)
    r2 = orchestrator.execute(
        WhatsAppMessageRequestDTO(
            phone=phone,
            message=f"{start.strftime('%d/%m/%Y')} e {end.strftime('%d/%m/%Y')}",
            source="twilio",
        )
    )
    first_room = "102" if "102" in r2.reply else "201"
    orchestrator.execute(
        WhatsAppMessageRequestDTO(phone=phone, message=first_room, source="twilio")
    )

    # 4. Nome -> opções 1/2
    r4 = orchestrator.execute(
        WhatsAppMessageRequestDTO(phone=phone, message="Maria Santos", source="twilio")
    )
    assert r4.success is True
    assert "1" in r4.reply and "2" in r4.reply

    # 5. Escolhe pagar agora
    r5 = orchestrator.execute(
        WhatsAppMessageRequestDTO(phone=phone, message="1", source="twilio")
    )
    assert r5.success is True
    assert "PIX" in r5.reply or "pagamento" in r5.reply.lower()

    persisted = repo.find_by_phone_number(phone)
    assert persisted is not None
    assert persisted.status == ReservationStatus.PENDING
    assert persisted.guest_name == "Maria Santos"

    assert cache.get(flow_key) is None
    session.close()
