"""
Reservation Context Service - formats reservation data for AI conversation context.

Retrieves active reservation information and formats it into a human-readable
context string that can be injected into the AI system prompt, allowing the
model to understand the current guest's reservation details.
"""
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.repositories.reservation_repository import ReservationRepository


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
    
    def get_context_for_phone(self, hotel_id: str, phone_number: str) -> str:
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
            reservation = self.reservation_repo.find_by_phone_number(phone_number, hotel_id)
            if not reservation:
                return ""
            
            # Skip if reservation is cancelled or no-show
            if reservation.status in (ReservationStatus.CANCELLED, ReservationStatus.NO_SHOW):
                return ""
            
            # Format reservation context
            context_parts = [
                "📋 **CONTEXTO DE RESERVA DO HÓSPEDE:**",
                f"  • Nome: {reservation.guest_name}",
                f"  • Status: {self._format_status(reservation.status)}",
            ]
            
            # Add check-in/check-out dates if available
            if reservation.stay_period and reservation.stay_period.start:
                context_parts.append(
                    f"  • Check-in: {reservation.stay_period.start.strftime('%d/%m/%Y')}"
                )
            if reservation.stay_period and reservation.stay_period.end:
                context_parts.append(
                    f"  • Check-out: {reservation.stay_period.end.strftime('%d/%m/%Y')}"
                )
            
            # Add room number if assigned
            if reservation.room_number:
                context_parts.append(f"  • Quarto: {reservation.room_number}")
            
            # Add total amount if available
            if reservation.total_amount:
                context_parts.append(f"  • Valor total: R$ {reservation.total_amount:.2f}")
            
            context_parts.append("")  # Empty line for readability
            
            return "\n".join(context_parts)
            
        except Exception:
            # Silently return empty context on error to avoid breaking conversation
            return ""
    
    @staticmethod
    def _format_status(status: ReservationStatus) -> str:
        """Format reservation status for display."""
        status_map = {
            ReservationStatus.PENDING: "Pendente",
            ReservationStatus.CONFIRMED: "Confirmada",
            ReservationStatus.CHECKED_IN: "Hóspede no hotel",
            ReservationStatus.CHECKED_OUT: "Saída realizada",
            ReservationStatus.CANCELLED: "Cancelada",
            ReservationStatus.NO_SHOW: "Não compareceu",
        }
        return status_map.get(status, status.name)
