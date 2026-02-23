"""
Application Layer Exceptions - errors in use-case orchestration.

These exceptions represent failures in business process coordination.
They wrap or translate domain exceptions for the interface layer.
"""


class ApplicationException(Exception):
    """Base exception for all application-level errors."""
    pass


class CheckInFailed(ApplicationException):
    """Raised when check-in process fails."""
    pass


class ConversationFailed(ApplicationException):
    """Raised when conversation orchestration fails."""
    pass


class AIServiceError(ApplicationException):
    """Raised when AI service call fails."""
    pass


class CacheError(ApplicationException):
    """Raised when cache operation fails."""
    pass


class MessagingError(ApplicationException):
    """Raised when message delivery fails."""
    pass


class InvalidInput(ApplicationException):
    """Raised when input validation fails."""
    pass
