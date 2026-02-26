"""
Reservation Context Service - formats reservation data for AI conversation context.

Retrieves active reservation information and formats it into a human-readable
context string that can be injected into the AI system prompt, allowing the
model to understand the current guest's reservation details.
"""
from typing import Optional
from datetime import datetime

from app.domain.repositories.reservation_repository import ReservationRepository
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.models import ReservationModel


class ReservationContextService:
    """
    Formats reservation context for AI conversations.
    
    Queries the reservation repository to find active reservations and
    formats them into context for the AI system prompt.
    """
    
    def __init__(self, reservation_repo: ReservationRepository):
        """
        Initialize reservation context service.
        
        Args:
            reservation_repo: Repository for accessing reservations
        """
        self.reservation_repo = reservation_repo
    
    def get_context_for_phone(self, phone_number: str) -> str:
        """
        Retrieve and format reservation context for a phone number.
        
        Queries the database for active reservations and returns a
        formatted context string for injection into AI prompts.
        
        Args:
            phone_number: Guest phone number
            
        Returns:
            Formatted reservation context string, or empty string if no active reservation
        """
        try:
            # Get raw reservation model from database to access full details
            session = SessionLocal()
            reservation_model: Optional[ReservationModel] = (
                session
                .query(ReservationModel)
                .filter_by(guest_phone=phone_number)
                .order_by(ReservationModel.created_at.desc())  # Get most recent
                .first()
            )
            session.close()
            
            if not reservation_model:
                return ""
            
            # Skip if reservation is cancelled or no-show
            if reservation_model.status in ("CANCELLED", "NO_SHOW"):
                return ""
            
            # Format reservation context
            context_parts = [
                "📋 **CONTEXTO DE RESERVA DO HÓSPEDE:**",
                f"  • Nome: {reservation_model.guest_name}",
                f"  • Status: {self._format_status(reservation_model.status)}",
            ]
            
            # Add check-in/check-out dates if available
            if reservation_model.check_in_date:
                context_parts.append(
                    f"  • Check-in: {reservation_model.check_in_date.strftime('%d/%m/%Y')}"
                )
            if reservation_model.check_out_date:
                context_parts.append(
                    f"  • Check-out: {reservation_model.check_out_date.strftime('%d/%m/%Y')}"
                )
            
            # Add room number if assigned
            if reservation_model.room_number:
                context_parts.append(f"  • Quarto: {reservation_model.room_number}")
            
            # Add total amount if available
            if reservation_model.total_amount:
                context_parts.append(f"  • Valor total: R$ {reservation_model.total_amount:.2f}")
            
            # Add notes if available
            if reservation_model.notes:
                context_parts.append(f"  • Notas: {reservation_model.notes}")
            
            context_parts.append("")  # Empty line for readability
            
            return "\n".join(context_parts)
            
        except Exception as e:
            # Silently return empty context on error to avoid breaking conversation
            print(f"Error getting reservation context: {str(e)}")
            return ""
    
    @staticmethod
    def _format_status(status: str) -> str:
        """Format reservation status for display."""
        status_map = {
            "PENDING": "Pendente",
            "CONFIRMED": "Confirmada",
            "CHECKED_IN": "Hóspede no hotel",
            "CHECKED_OUT": "Saída realizada",
            "CANCELLED": "Cancelada",
            "NO_SHOW": "Não compareceu",
        }
        return status_map.get(status, status)
