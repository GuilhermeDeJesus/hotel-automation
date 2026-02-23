import json
import pytest
from app.application.use_cases.conversation import ConversationUseCase
from tests.unit.mocks.ai_service_mock import AIServiceMock
from app.infrastructure.persistence.memory.reservation_repository_memory import (
    ReservationRepositoryMemory,
)


class RedisCacheMock:
    """Mock Redis cache that stores data in memory (simulates Redis behavior)."""

    def __init__(self):
        self.store = {}

    def get(self, phone: str):
        """Get cached conversation history."""
        data = self.store.get(phone)
        if data:
            return json.loads(data) if isinstance(data, str) else data
        return None

    def set(self, phone: str, data, ttl_seconds: int = 3600):
        """Set cached conversation history with optional TTL."""
        self.store[phone] = json.dumps(data) if not isinstance(data, str) else data
    
    def delete(self, key: str):
        """Delete cached data."""
        self.store.pop(key, None)
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self.store
    
    def clear(self):
        """Clear all cached data."""
        self.store.clear()


class DummyMessenger:
    def __init__(self):
        self.sent = []

    def send(self, phone, message):
        self.sent.append((phone, message))


def test_conversation_use_case_single_turn():
    """Test a single turn conversation."""
    ai = AIServiceMock({"hello": "hi there"})
    repo = ReservationRepositoryMemory()
    cache = RedisCacheMock()
    messenger = DummyMessenger()

    use_case = ConversationUseCase(
        ai_service=ai, reservation_repo=repo, cache_repository=cache, messaging=messenger
    )

    phone = "556199999999"
    answer = use_case.execute(phone, "hello")

    assert answer == "hi there"
    assert messenger.sent == [(phone, "hi there")]
    assert cache.get(phone)[-1]["role"] == "assistant"


def test_conversation_use_case_multi_turn_with_redis():
    """Test multi-turn conversation with history maintained in Redis cache."""
    # prepare a mock AI that responds based on context
    responses = {
        "what is my name?": "I don't know, you haven't told me",
        "my name is John": "Nice to meet you, John!",
    }
    ai = AIServiceMock(responses)
    repo = ReservationRepositoryMemory()
    cache = RedisCacheMock()  # Simulates Redis (in-memory for testing)
    messenger = DummyMessenger()

    use_case = ConversationUseCase(
        ai_service=ai, reservation_repo=repo, cache_repository=cache, messaging=messenger
    )

    phone = "556199999999"

    # Turn 1: User asks what is their name
    answer1 = use_case.execute(phone, "what is my name?")
    assert answer1 == "I don't know, you haven't told me"
    assert len(cache.get(phone)) == 2  # user + assistant

    # Turn 2: User sends their name
    answer2 = use_case.execute(phone, "my name is John")
    assert answer2 == "Nice to meet you, John!"
    # cache now has 4 messages: first Q&A + second Q&A
    cached_history = cache.get(phone)
    assert len(cached_history) == 4
    assert cached_history[0]["content"] == "what is my name?"
    assert cached_history[2]["content"] == "my name is John"

    # Turn 3: Ask again - AI receives full history as context
    answer3 = use_case.execute(phone, "what is my name?")
    # AI mock will respond based on the prompt (in real scenario, would have context)
    # For this test, verify history was passed to AI
    assert ai.last_call[0] == "chat"
    # The messages list passed to AI should include all previous messages
    assert len(ai.last_call[1]) >= 4  # At least 4 messages for full context

    # Cache should grow (6 now: Q1, A1, Q2, A2, Q3, A3)
    final_history = cache.get(phone)
    assert len(final_history) == 6
    assert final_history[-1]["role"] == "assistant"

    # Verify messanger was called 3 times
    assert len(messenger.sent) == 3


def test_conversation_cache_persistence():
    """Test that cache persists between different use case invocations."""
    ai = AIServiceMock({"hello": "hi"})
    repo = ReservationRepositoryMemory()
    cache = RedisCacheMock()  # shared cache instance
    phone = "556199999999"

    # First conversation instance
    uc1 = ConversationUseCase(
        ai_service=ai,
        reservation_repo=repo,
        cache_repository=cache,
        messaging=None,
    )
    uc1.execute(phone, "hello")
    history_after_first = cache.get(phone)

    # Second conversation instance (new object, same cache)
    uc2 = ConversationUseCase(
        ai_service=ai,
        reservation_repo=repo,
        cache_repository=cache,  # same cache!
        messaging=None,
    )
    uc2.execute(phone, "hello")
    history_after_second = cache.get(phone)

    # Second use case should see history from first
    assert len(history_after_second) == 4  # 2 turns = 4 messages
    assert history_after_second[0] == history_after_first[0]


if __name__ == "__main__":
    pytest.main([__file__])
