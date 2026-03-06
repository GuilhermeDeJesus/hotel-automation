from app.application.use_cases.conversation import ConversationUseCase
from app.infrastructure.cache.redis_repository import RedisRepository
from app.infrastructure.persistence.memory.reservation_repository_memory import ReservationRepositoryMemory
from tests.unit.mocks.ai_service_mock import AIServiceMock


class DummyReservationContextService:
    def get_context_for_phone(self, phone: str) -> str:
        return ""


class DummyHotelContextService:
    def get_context(self) -> str:
        return ""


def test_conversation_persists_in_real_redis():
    phone = "559999100001"
    cache = RedisRepository()
    cache.delete(phone)

    use_case = ConversationUseCase(
        ai_service=AIServiceMock({"olá": "Olá! Como posso ajudar?"}),
        reservation_repo=ReservationRepositoryMemory(),
        cache_repository=cache,
        context_service=DummyReservationContextService(),
        hotel_context_service=DummyHotelContextService(),
        messaging=None,
        logger=None,
    )

    answer = use_case.execute(phone, "olá")

    assert answer == "Olá! Como posso ajudar?"

    history = cache.get(phone)
    assert history is not None
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "olá"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Olá! Como posso ajudar?"
