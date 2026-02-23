"""
Message Value Object - represents a single message in a conversation.
"""
from typing import Literal


class Message:
    """
    Immutable Value Object representing a message in a conversation.
    
    Enforces invariants:
    - role must be 'user', 'assistant', or 'system'
    - content must not be empty
    """
    
    VALID_ROLES = {"user", "assistant", "system"}
    
    def __init__(self, role: str, content: str):
        if role not in self.VALID_ROLES:
            raise ValueError(f"Invalid role '{role}'. Must be one of {self.VALID_ROLES}")
        
        if not content or not content.strip():
            raise ValueError("Message content cannot be empty")
        
        self._role = role
        self._content = content.strip()
    
    @property
    def role(self) -> str:
        return self._role
    
    @property
    def content(self) -> str:
        return self._content
    
    def to_dict(self) -> dict:
        """Convert to dictionary format for API serialization."""
        return {
            "role": self._role,
            "content": self._content
        }
    
    def is_user_message(self) -> bool:
        return self._role == "user"
    
    def is_assistant_message(self) -> bool:
        return self._role == "assistant"
    
    def is_system_message(self) -> bool:
        return self._role == "system"
    
    def __repr__(self) -> str:
        return f"Message(role='{self._role}', content='{self._content[:50]}...' if len > 50)"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Message):
            return False
        return self._role == other._role and self._content == other._content
    
    def __hash__(self) -> int:
        return hash((self._role, self._content))
