"""
Create Support Ticket Use Case - 6.6 Resolução de problemas automatizada.

Hóspede reporta problema (ex: ar condicionado) → bot cria ticket e notifica.
"""
from dataclasses import dataclass
from typing import Optional
import uuid

from app.domain.repositories.reservation_repository import ReservationRepository
from app.domain.repositories.support_ticket_repository import SupportTicketRepository


@dataclass
class CreateSupportTicketRequestDTO:
    phone: str
    description: str
    category: str = "GENERAL"


@dataclass
class CreateSupportTicketResponseDTO:
    success: bool
    message: str
    ticket_id: Optional[str] = None


class CreateSupportTicketUseCase:
    """6.6 Cria ticket de suporte e notifica hóspede."""

    def __init__(
        self,
        reservation_repository: ReservationRepository,
        ticket_repository: SupportTicketRepository,
    ):
        self.reservation_repository = reservation_repository
        self.ticket_repository = ticket_repository

    def execute(self, request: CreateSupportTicketRequestDTO) -> CreateSupportTicketResponseDTO:
        reservation = self.reservation_repository.find_by_phone_number(request.phone)
        if not reservation:
            return CreateSupportTicketResponseDTO(
                success=False,
                message="Nenhuma reserva encontrada.",
            )

        if reservation.status.name not in ("CHECKED_IN", "CONFIRMED"):
            return CreateSupportTicketResponseDTO(
                success=False,
                message="Só é possível abrir chamado durante a estadia ou reserva confirmada.",
            )

        ticket_id = str(uuid.uuid4())[:8]
        self.ticket_repository.save(
            ticket_id=ticket_id,
            reservation_id=reservation.id,
            description=request.description,
            category=request.category,
        )

        return CreateSupportTicketResponseDTO(
            success=True,
            message=(
                f"✅ Chamado #{ticket_id} registrado!\n\n"
                "Nossa equipe foi acionada e deve resolver em até 30 minutos.\n"
                "Em caso de urgência, ligue para a recepção."
            ),
            ticket_id=ticket_id,
        )
