"""
API Schemas (Pydantic Models) - HTTP request/response validation.

These schemas are used by FastAPI to validate incoming requests
and serialize responses. They are specific to the HTTP interface.

Separate from Application DTOs which are used for internal layer communication.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class WhatsAppMessageRequest(BaseModel):
    """Schema for incoming WhatsApp messages via webhook."""
    
    phone: str = Field(..., description="Sender phone number", min_length=10, max_length=20)
    message: str = Field(..., description="Message content", min_length=1, max_length=2000)
    timestamp: Optional[int] = Field(None, description="Message timestamp (Unix)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone": "5511999999999",
                "message": "Olá, quero fazer check-in",
                "timestamp": 1708426800
            }
        }
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """Validate phone number format."""
        if not v or not v.isdigit():
            raise ValueError("Phone number must contain only digits")
        return v


class CheckInRequest(BaseModel):
    """Schema for check-in API endpoint."""
    
    phone: str = Field(..., description="Guest phone number", min_length=10)
    name: Optional[str] = Field(None, description="Guest name")
    room: Optional[str] = Field(None, description="Room number")
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone": "5511999999999",
                "name": "João Silva",
                "room": "101"
            }
        }


class ConversationRequest(BaseModel):
    """Schema for conversation endpoint."""
    
    phone: str = Field(..., description="User phone number", min_length=10)
    message: str = Field(..., description="Message text", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone": "5511999999999",
                "message": "Preciso de toalhas extras"
            }
        }


class ConversationResponse(BaseModel):
    """Schema for conversation response."""
    
    phone: str = Field(..., description="User phone number")
    response: str = Field(..., description="AI response")
    timestamp: int = Field(..., description="Response timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone": "5511999999999",
                "response": "Vou enviar toalhas extras para você agora!",
                "timestamp": 1708426900
            }
        }


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    status: int = Field(..., description="HTTP status code")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "INVALID_PHONE",
                "message": "Phone number format is invalid",
                "status": 400
            }
        }
