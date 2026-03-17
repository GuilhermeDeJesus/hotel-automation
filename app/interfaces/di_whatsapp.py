"""
DI container para fluxos de WhatsApp.

Extraído de `app/interfaces/dependencies.py` para evitar conflito com o
pacote `app.interfaces.dependencies` usado pelos endpoints SaaS.
"""
from collections.abc import Generator

from app.infrastructure.persistence.sql.database import SessionLocal, init_db
from app.infrastructure.persistence.sql.reservation_repository_sql import ReservationRepositorySQL
from app.infrastructure.persistence.sql.hotel_repository_sql import HotelRepositorySQL
from app.infrastructure.persistence.sql.room_repository_sql import RoomRepositorySQL
from app.infrastructure.persistence.sql.hotel_repository_sql import HotelRepositorySQL
from app.infrastructure.persistence.sql.saas_repository_sql import SaaSRepositorySQL
from app.infrastructure.persistence.sql.payment_repository_sql import PaymentRepositorySQL
from app.infrastructure.payment.payment_provider_factory import get_payment_provider
from app.infrastructure.persistence.memory.reservation_repository_memory import ReservationRepositoryMemory
from app.infrastructure.cache.redis_repository import RedisRepository
from app.infrastructure.ai.openai_client import OpenAIClient
from app.infrastructure.logging.conversation_logger import ConversationLogger
from app.application.use_cases.cancel_reservation import CancelReservationUseCase
from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
from app.application.use_cases.create_reservation import CreateReservationUseCase
from app.application.use_cases.checkout_via_whatsapp import CheckoutViaWhatsAppUseCase
from app.application.use_cases.handle_whatsapp_message import HandleWhatsAppMessageUseCase
from app.application.use_cases.confirm_reservation import ConfirmReservationUseCase
from app.application.use_cases.conversation import ConversationUseCase
from app.application.use_cases.extend_reservation import ExtendReservationUseCase
from app.application.use_cases.handle_payment_webhook import HandlePaymentWebhookUseCase
from app.application.use_cases.pre_checkin import PreCheckInUseCase
from app.application.use_cases.create_support_ticket import CreateSupportTicketUseCase
from app.application.use_cases.room_order import RoomOrderUseCase
from app.infrastructure.persistence.sql.support_ticket_repository_sql import (
    SupportTicketRepositorySQL,
    RoomOrderRepositorySQL,
)
from app.application.services.reservation_context_service import ReservationContextService
from app.application.services.hotel_context_service import HotelContextService


init_db()


def get_checkin_use_case() -> CheckInViaWhatsAppUseCase:
    session = SessionLocal()
    reservation_repo = ReservationRepositorySQL(session)
    cache_repo = RedisRepository()
    return CheckInViaWhatsAppUseCase(
        reservation_repository=reservation_repo,
        cache_repository=cache_repo,
    )


def get_reservation_context_service() -> ReservationContextService:
    session = SessionLocal()
    reservation_repo = ReservationRepositorySQL(session)
    return ReservationContextService(reservation_repo=reservation_repo)


def get_hotel_context_service() -> HotelContextService:
    session = SessionLocal()
    hotel_repo = HotelRepositorySQL(session)
    return HotelContextService(hotel_repository=hotel_repo)


def get_conversation_use_case() -> ConversationUseCase:
    ai_service = OpenAIClient()
    session = SessionLocal()
    reservation_repo = ReservationRepositorySQL(session)
    cache_repository = RedisRepository()
    context_service = get_reservation_context_service()
    hotel_context_service = get_hotel_context_service()
    logger = ConversationLogger()

    return ConversationUseCase(
        ai_service=ai_service,
        reservation_repo=reservation_repo,
        cache_repository=cache_repository,
        context_service=context_service,
        hotel_context_service=hotel_context_service,
        messaging=None,
        logger=logger,
    )


def get_whatsapp_message_use_case() -> HandleWhatsAppMessageUseCase:
    checkin_use_case = get_checkin_use_case()
    conversation_use_case = get_conversation_use_case()

    session = SessionLocal()
    reservation_repo = ReservationRepositorySQL(session)
    room_repo = RoomRepositorySQL(session)
    hotel_repo = HotelRepositorySQL(session)

    checkout_use_case = CheckoutViaWhatsAppUseCase(reservation_repository=reservation_repo)
    cancel_reservation_use_case = CancelReservationUseCase(reservation_repository=reservation_repo)
    create_reservation_use_case = CreateReservationUseCase(
        reservation_repository=reservation_repo,
        room_repository=room_repo,
    )
    confirm_reservation_use_case = ConfirmReservationUseCase(reservation_repo)
    extend_reservation_use_case = ExtendReservationUseCase(
        reservation_repository=reservation_repo,
        room_repository=room_repo,
    )
    cache_repository = RedisRepository()

    pre_checkin_use_case = PreCheckInUseCase(reservation_repository=reservation_repo)
    support_ticket_use_case = CreateSupportTicketUseCase(
        reservation_repository=reservation_repo,
        ticket_repository=SupportTicketRepositorySQL(session),
    )
    room_order_use_case = RoomOrderUseCase(
        reservation_repository=reservation_repo,
        order_repository=RoomOrderRepositorySQL(session),
    )

    return HandleWhatsAppMessageUseCase(
        checkin_use_case=checkin_use_case,
        checkout_use_case=checkout_use_case,
        cancel_reservation_use_case=cancel_reservation_use_case,
        create_reservation_use_case=create_reservation_use_case,
        conversation_use_case=conversation_use_case,
        confirm_reservation_use_case=confirm_reservation_use_case,
        extend_reservation_use_case=extend_reservation_use_case,
        reservation_repository=reservation_repo,
        cache_repository=cache_repository,
        room_repository=room_repo,
        hotel_repository=hotel_repo,
        payment_provider=get_payment_provider(),
        payment_repository=PaymentRepositorySQL(session),
        pre_checkin_use_case=pre_checkin_use_case,
        support_ticket_use_case=support_ticket_use_case,
        room_order_use_case=room_order_use_case,
    )

