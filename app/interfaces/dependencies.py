"""
Dependency Injection Container - Composition root for the application.

Configures and provides instances of use-cases with all dependencies wired.
This is the single place where concrete implementations are instantiated.
All other layers work with abstractions (interfaces).
"""
import os

from app.infrastructure.persistence.sql.database import SessionLocal, init_db
from app.infrastructure.persistence.sql.reservation_repository_sql import ReservationRepositorySQL
from app.infrastructure.persistence.sql.hotel_repository_sql import HotelRepositorySQL
from app.infrastructure.persistence.sql.room_repository_sql import RoomRepositorySQL
from app.infrastructure.persistence.memory.reservation_repository_memory import ReservationRepositoryMemory
from app.infrastructure.cache.redis_repository import RedisRepository
from app.infrastructure.ai.openai_client import OpenAIClient
from app.infrastructure.logging.conversation_logger import ConversationLogger
from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
from app.application.use_cases.handle_whatsapp_message import HandleWhatsAppMessageUseCase
from app.application.use_cases.confirm_reservation import ConfirmReservationUseCase
from app.application.use_cases.conversation import ConversationUseCase
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
    
    # Simple in-memory cache
    class InMemoryCache:
        def __init__(self):
            self.store = {}
        
        def get(self, key: str):
            return self.store.get(key)
        
        def set(self, key: str, value, ttl_seconds: int = 3600):
            self.store[key] = value
        
        def delete(self, key: str):
            self.store.pop(key, None)
        
        def exists(self, key: str) -> bool:
            return key in self.store
        
        def clear(self):
            self.store.clear()
    
    cache_repository = InMemoryCache()
    
    # Create mock context services for testing
    class MockContextService:
        def get_context_for_phone(self, phone: str) -> str:
            return ""  # No context in test mode

    class MockHotelContextService:
        def get_context(self) -> str:
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
    
    confirm_reservation_use_case = ConfirmReservationUseCase(reservation_repo)
    cache_repository = RedisRepository()
    
    return HandleWhatsAppMessageUseCase(
        checkin_use_case=checkin_use_case,
        conversation_use_case=conversation_use_case,
        confirm_reservation_use_case=confirm_reservation_use_case,
        cache_repository=cache_repository,
        room_repository=room_repo,
    )