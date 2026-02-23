"""
Dependency Injection Container - Composition root for the application.

Configures and provides instances of use-cases with all dependencies wired.
This is the single place where concrete implementations are instantiated.
All other layers work with abstractions (interfaces).
"""
import os

from app.infrastructure.persistence.sql.database import SessionLocal, init_db
from app.infrastructure.persistence.sql.reservation_repository_sql import ReservationRepositorySQL
from app.infrastructure.persistence.memory.reservation_repository_memory import ReservationRepositoryMemory
from app.infrastructure.cache.redis_repository import RedisRepository
from app.infrastructure.ai.openai_client import OpenAIClient
from app.infrastructure.logging.conversation_logger import ConversationLogger
from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
from app.application.use_cases.conversation import ConversationUseCase

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
        - ConversationLogger for persistent interaction logging
    """
    # Instantiate concrete implementations
    ai_service = OpenAIClient()
    session = SessionLocal()
    reservation_repo = ReservationRepositorySQL(session)
    cache_repository = RedisRepository()
    logger = ConversationLogger()  # Production logger with JSON persistence
    
    # Optional: messaging provider (not yet implemented)
    # messaging_provider = WhatsAppClient()
    
    # Return use-case with dependencies
    return ConversationUseCase(
        ai_service=ai_service,
        reservation_repo=reservation_repo,
        cache_repository=cache_repository,
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
    
    return ConversationUseCase(
        ai_service=ai_service,
        reservation_repo=reservation_repo,
        cache_repository=cache_repository,
        messaging=None,
        logger=None  # No logging in test mode
    )