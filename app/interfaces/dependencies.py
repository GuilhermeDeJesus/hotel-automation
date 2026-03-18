"""
Dependency Injection Container - Composition root for the application.

Configures and provides instances of use-cases with all dependencies wired.
This is the single place where concrete implementations are instantiated.
All other layers work with abstractions (interfaces).
"""
import os
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
from app.infrastructure.persistence.sql.hotel_media_repository_sql import HotelMediaRepositorySQL
from app.application.use_cases.cancel_reservation import CancelReservationUseCase
from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
from app.application.use_cases.create_reservation import CreateReservationUseCase
from app.application.use_cases.checkout_via_whatsapp import CheckoutViaWhatsAppUseCase
from app.application.use_cases.handle_whatsapp_message import HandleWhatsAppMessageUseCase
from app.application.use_cases.confirm_reservation import ConfirmReservationUseCase
from app.application.use_cases.conversation import ConversationUseCase
from app.application.use_cases.extend_reservation import ExtendReservationUseCase
from app.application.use_cases.get_saas_dashboard import GetSaaSDashboardUseCase
from app.application.use_cases.get_journey_funnel import GetJourneyFunnelUseCase
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

# Initialize database tables on module load
init_db()


def get_checkin_use_case() -> CheckInViaWhatsAppUseCase:
    """
    Get CheckInViaWhatsAppUseCase with all dependencies injected.
    
    Returns:
        Configured CheckInViaWhatsAppUseCase instance
        
    Note:
        Dependencies are abstractions from domain layer:
        - ReservationRepository (abstract interface)
        - CacheRepository (abstract interface)
    """
    # Create database session
    session = SessionLocal()
    
    # Instantiate concrete implementations
    reservation_repo = ReservationRepositorySQL(session)
    cache_repo = RedisRepository()
    
    # Return use-case with dependencies
    return CheckInViaWhatsAppUseCase(
        reservation_repository=reservation_repo,
        cache_repository=cache_repo
    )


def get_reservation_context_service() -> ReservationContextService:
    """
    Get ReservationContextService with dependencies injected.
    
    Returns:
        Configured ReservationContextService instance
    """
    session = SessionLocal()
    reservation_repo = ReservationRepositorySQL(session)
    return ReservationContextService(reservation_repo=reservation_repo)


def get_hotel_context_service() -> HotelContextService:
    """
    Get HotelContextService with dependencies injected.
    
    Returns:
        Configured HotelContextService instance
    """
    session = SessionLocal()
    hotel_repo = HotelRepositorySQL(session)
    return HotelContextService(hotel_repository=hotel_repo)


def get_conversation_use_case() -> ConversationUseCase:
    """
    Get ConversationUseCase with all dependencies injected.
    
    Returns:
        Configured ConversationUseCase instance
        
    Note:
        Dependencies are abstractions from domain layer:
        - AIService (abstract interface)
        - ReservationRepository (abstract interface)
        - CacheRepository (abstract interface)
        - ReservationContextService for fetching guest context
        - ConversationLogger for persistent interaction logging
    """
    # Instantiate concrete implementations
    ai_service = OpenAIClient()
    session = SessionLocal()
    reservation_repo = ReservationRepositorySQL(session)
    cache_repository = RedisRepository()
    context_service = get_reservation_context_service()
    hotel_context_service = get_hotel_context_service()
    logger = ConversationLogger()  # Production logger with JSON persistence
    
    # Optional: messaging provider (not yet implemented)
    # messaging_provider = WhatsAppClient()
    
    # Return use-case with dependencies
    return ConversationUseCase(
        ai_service=ai_service,
        reservation_repo=reservation_repo,
        cache_repository=cache_repository,
        context_service=context_service,
        hotel_context_service=hotel_context_service,
        messaging=None,  # Optional messaging provider
        logger=logger  # Production conversation logger
    )


def get_conversation_use_case_memory() -> ConversationUseCase:
    """
    Get ConversationUseCase for testing (in-memory repositories).
    
    Returns:
        ConversationUseCase configured with memory repositories
        
    Use this for:
    - Unit tests
    - Development without dependencies
    - CI/CD pipelines
    """
    from app.tests.unit.mocks.ai_service_mock import AIServiceMock
    
    # Use in-memory implementations
    ai_service = AIServiceMock(responses={})
    reservation_repo = ReservationRepositoryMemory()
    
    # In-memory cache de conversa (multi-tenant)
    class InMemoryConversationCache:
        def __init__(self):
            self.store: dict[str, object] = {}

        def _key(self, hotel_id: str, phone: str) -> str:
            return f"conversation:{hotel_id}:{phone}"

        def get(self, hotel_id: str, phone: str):
            return self.store.get(self._key(hotel_id, phone))

        def set(
            self,
            hotel_id: str,
            phone: str,
            data: object,
            ttl_seconds: int = 3600,
        ):
            # TTL não é aplicado no modo memória.
            self.store[self._key(hotel_id, phone)] = data

    cache_repository = InMemoryConversationCache()
    
    # Create mock context services for testing
    class MockContextService:
        def get_context_for_phone(self, hotel_id: str, phone: str) -> str:
            return ""  # No context in test mode

    class MockHotelContextService:
        def get_context(self, hotel_id=None) -> str:
            return ""  # No hotel context in test mode
    
    context_service = MockContextService()
    hotel_context_service = MockHotelContextService()
    
    return ConversationUseCase(
        ai_service=ai_service,
        reservation_repo=reservation_repo,
        cache_repository=cache_repository,
        context_service=context_service,
        hotel_context_service=hotel_context_service,
        messaging=None,
        logger=None  # No logging in test mode
    )


def get_whatsapp_message_use_case() -> HandleWhatsAppMessageUseCase:
    """
    Get HandleWhatsAppMessageUseCase with dependencies injected.

    Returns:
        Configured HandleWhatsAppMessageUseCase instance
    """
    checkin_use_case = get_checkin_use_case()
    conversation_use_case = get_conversation_use_case()
    
    session = SessionLocal()
    reservation_repo = ReservationRepositorySQL(session)
    room_repo = RoomRepositorySQL(session)
    hotel_repo = HotelRepositorySQL(session)
    hotel_media_repo = HotelMediaRepositorySQL(session)

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
        hotel_media_repository=hotel_media_repo,
    )


def get_payment_webhook_use_case() -> HandlePaymentWebhookUseCase:
    """Get HandlePaymentWebhookUseCase com dependências injetadas."""
    session = SessionLocal()
    payment_repo = PaymentRepositorySQL(session)
    reservation_repo = ReservationRepositorySQL(session)
    return HandlePaymentWebhookUseCase(
        payment_repository=payment_repo,
        reservation_repository=reservation_repo,
    )


def get_saas_dashboard_use_case() -> Generator[GetSaaSDashboardUseCase, None, None]:
    session = SessionLocal()
    saas_repository = SaaSRepositorySQL(session)
    cache_repository = RedisRepository()
    try:
        yield GetSaaSDashboardUseCase(
            saas_repository=saas_repository,
            cache_repository=cache_repository,
            cache_ttl_seconds=120,
        )
    finally:
        session.close()


def get_journey_funnel_use_case() -> Generator[GetJourneyFunnelUseCase, None, None]:
    session = SessionLocal()
    saas_repository = SaaSRepositorySQL(session)
    reservation_repository = ReservationRepositorySQL(session)
    try:
        yield GetJourneyFunnelUseCase(
            saas_repository=saas_repository,
            reservation_repository=reservation_repository,
        )
    finally:
        session.close()