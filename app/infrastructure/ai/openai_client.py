import os
from typing import Any, Dict, List

import openai

from app.application.services.ai_service import AIService


class OpenAIClient(AIService):
    """Concrete AIService that calls the OpenAI API using the new SDK (v2.x+).

    This implementation reads the API key from the `OPENAI_API_KEY`
    environment variable when instantiated. It uses the modern OpenAI SDK
    with the `client.chat.completions.create()` and `client.completions.create()`
    methods. Additional keyword arguments are passed through to these methods.
    """

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set")
        # Initialize the new OpenAI client with API key
        self.client = openai.OpenAI(api_key=key)

    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Send a chat message to OpenAI and return the response."""
        response = self.client.chat.completions.create(
            model=kwargs.pop("model", "gpt-3.5-turbo"),
            messages=messages,
            **kwargs,
        )
        # Extract the main content from the response
        return {
            "content": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        }

    def complete(self, prompt: str, **kwargs) -> str:
        """Send a completion request to OpenAI and return the text."""
        response = self.client.completions.create(
            model=kwargs.pop("model", "gpt-3.5-turbo-instruct"),
            prompt=prompt,
            **kwargs,
        )
        # return text from first choice
        return response.choices[0].text

