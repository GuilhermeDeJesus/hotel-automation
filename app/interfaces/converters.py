"""
Converters - Transform between different representation layers.

These converters map between:
- API Schemas (Pydantic) from HTTP interface
- Application DTOs for inter-layer communication
- Domain objects for business logic

This explicit mapping makes layer boundaries clear.
"""
from app.interfaces import schemas
from app.application import dto


class RequestConverters:
    """Convert HTTP requests to Application DTOs."""
    
    @staticmethod
    def whatsapp_to_conversation_dto(req: schemas.WhatsAppMessageRequest) -> dict:
        """
        Convert WhatsApp schema to conversation parameters.
        
        Args:
            req: Incoming WhatsApp message schema
            
        Returns:
            Dict with phone and message for use-case
        """
        return {
            "phone": req.phone,
            "message": req.message
        }
    
    @staticmethod
    def checkin_request_to_dto(req: schemas.CheckInRequest) -> dto.CheckinRequestDTO:
        """
        Convert check-in schema to DTO.
        
        Args:
            req: Incoming check-in request schema
            
        Returns:
            CheckinRequestDTO for use-case processing
        """
        return dto.CheckinRequestDTO(
            phone=req.phone,
            name=req.name,
            room=req.room
        )


class ResponseConverters:
    """Convert Application DTOs to HTTP Responses."""
    
    @staticmethod
    def checkin_dto_to_response(checkin_dto: dto.CheckinResponseDTO) -> schemas.ConversationResponse:
        """
        Convert check-in DTO to response schema.
        
        Args:
            checkin_dto: Check-in response DTO
            
        Returns:
            ConversationResponse schema for HTTP
        """
        import time
        return schemas.ConversationResponse(
            phone="",  # Set by controller
            response=checkin_dto.message,
            timestamp=int(time.time())
        )
    
    @staticmethod
    def error_to_response(error: Exception) -> schemas.ErrorResponse:
        """
        Convert exception to error response schema.
        
        Args:
            error: Exception that occurred
            
        Returns:
            ErrorResponse schema for HTTP
        """
        # Import here to avoid circular imports
        from app.interfaces.exceptions import APIException, InternalServerError
        
        if isinstance(error, APIException):
            return schemas.ErrorResponse(
                error=error.error_code,
                message=error.message,
                status=error.status_code
            )
        else:
            # Wrap unexpected errors
            internal_error = InternalServerError(str(error))
            return schemas.ErrorResponse(
                error=internal_error.error_code,
                message=internal_error.message,
                status=internal_error.status_code
            )
