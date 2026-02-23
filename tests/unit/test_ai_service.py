from app.application.services.ai_service import AIService
from tests.unit.mocks.ai_service_mock import AIServiceMock


def test_ai_service_mock_complete():
    responses = {"hello": "world"}
    ai = AIServiceMock(responses)
    result = ai.complete("hello")
    assert result == "world"
    assert ai.last_call[0] == "complete"


def test_ai_service_mock_chat():
    responses = {"hi": "hey"}
    ai = AIServiceMock(responses)
    messages = [{"role": "user", "content": "hi"}]
    resp = ai.chat(messages)
    assert resp["choices"][0]["message"]["content"] == "hey"
    assert ai.last_call[0] == "chat"
