from typing import Any, Dict, List

from app.application.services.ai_service import AIService


class AIServiceMock(AIService):
    """Simple in-memory mock of AIService for unit tests."""

    def __init__(self, responses: Dict[str, str] | None = None):
        # responses maps either prompts or conversation ids to outputs
        self._responses = responses or {}
        self.last_call = None

    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        # store last call for assertions
        self.last_call = ("chat", messages, kwargs)
        # find by last user message
        if messages and isinstance(messages[-1].get("content"), str):
            key = messages[-1]["content"]
            return {"choices": [{"message": {"content": self._responses.get(key, "")}}]}
        return {"choices": []}

    def complete(self, prompt: str, **kwargs) -> str:
        self.last_call = ("complete", prompt, kwargs)
        return self._responses.get(prompt, "")
