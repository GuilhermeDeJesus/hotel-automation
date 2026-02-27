"""
Interaction Logger Interface - contract for conversation interaction logging.

Application use-cases should depend on this abstraction instead of
concrete infrastructure loggers.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class InteractionLogger(ABC):
    """Interface for logging conversation interactions."""

    @abstractmethod
    def log_interaction(
        self,
        phone: str,
        user_message: str,
        ai_response: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        model: str = "gpt-3.5-turbo",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist a single interaction entry."""
        pass
