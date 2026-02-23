"""
Domain Layer Exceptions - core business rule violations.

These exceptions represent invariant violations in the domain model.
They should be caught and handled at higher layers (Application, Interfaces).
"""


class DomainException(Exception):
    """Base exception for all domain-level errors."""
    pass


class InvalidPhoneNumber(DomainException):
    """Raised when phone number format is invalid."""
    pass


class InvalidReservationStatus(DomainException):
    """Raised when reservation status transition is invalid."""
    pass


class InvalidCheckInState(DomainException):
    """Raised when check-in is attempted in invalid reservation state."""
    pass


class ReservationNotFound(DomainException):
    """Raised when reservation lookup by ID fails."""
    pass


class InvalidMessage(DomainException):
    """Raised when message violates domain rules."""
    pass
