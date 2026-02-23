"""
Interface Layer Exceptions - HTTP/API level errors.

These exceptions are caught by the web framework and converted to HTTP responses.
"""


class APIException(Exception):
    """Base exception for API/HTTP level errors."""
    
    def __init__(self, message: str, status_code: int = 500, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        super().__init__(message)
    
    def to_dict(self):
        """Convert exception to API response format."""
        return {
            "error": self.error_code,
            "message": self.message,
            "status": self.status_code
        }


class BadRequest(APIException):
    """400 Bad Request."""
    def __init__(self, message: str):
        super().__init__(message, status_code=400, error_code="BAD_REQUEST")


class Unauthorized(APIException):
    """401 Unauthorized."""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401, error_code="UNAUTHORIZED")


class Forbidden(APIException):
    """403 Forbidden."""
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403, error_code="FORBIDDEN")


class NotFound(APIException):
    """404 Not Found."""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404, error_code="NOT_FOUND")


class Conflict(APIException):
    """409 Conflict."""
    def __init__(self, message: str):
        super().__init__(message, status_code=409, error_code="CONFLICT")


class InternalServerError(APIException):
    """500 Internal Server Error."""
    def __init__(self, message: str = "Internal server error"):
        super().__init__(message, status_code=500, error_code="INTERNAL_ERROR")


class ServiceUnavailable(APIException):
    """503 Service Unavailable."""
    def __init__(self, message: str = "Service unavailable"):
        super().__init__(message, status_code=503, error_code="SERVICE_UNAVAILABLE")
