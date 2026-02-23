"""
Domain Layer Value Objects - Immutable domain primitives with invariants.
"""
from app.domain.value_objects.phone_number import PhoneNumber
from app.domain.value_objects.message import Message

__all__ = [
    "PhoneNumber",
    "Message",
]
