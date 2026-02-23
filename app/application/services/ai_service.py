from abc import ABC, abstractmethod
from typing import Any, Dict, List


class AIService(ABC):
    """Interface for an AI/Large Language Model provider.

    The use cases should depend on this interface rather than a concrete
    implementation, allowing easy substitution (e.g. real OpenAI client, a
    mock for tests, or another provider).
    """

    @abstractmethod
    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Send a conversation-style prompt and receive a model response.

        Parameters:
            messages: list of objects with keys `role` and `content`, same as
                the OpenAI ChatCompletion API.
            **kwargs: provider-specific extra options (temperature, max_tokens,
                etc.).

        Returns:
            A dictionary containing the raw provider response.
        """
        pass

    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> str:
        """Send a text prompt and get back generated text.

        This mirrors the `Completion` API from OpenAI/others.
        """
        pass
