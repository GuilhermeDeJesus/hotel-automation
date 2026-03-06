"""
Pre-Check-In Use Case - 6.1 Check-in antecipado.

Coleta documentos (CPF), horário estimado de chegada e aceita termos.
"""
from dataclasses import dataclass
from typing import Optional

from app.domain.repositories.reservation_repository import ReservationRepository


@dataclass
class PreCheckInRequestDTO:
    phone: str
    guest_document: str
    estimated_arrival_time: Optional[str] = None


@dataclass
class PreCheckInResponseDTO:
    success: bool
    message: str


class PreCheckInUseCase:
    """6.1 Check-in antecipado - coleta documentos e horário."""

    def __init__(self, reservation_repository: ReservationRepository):
        self.reservation_repository = reservation_repository

    def execute(self, request: PreCheckInRequestDTO) -> PreCheckInResponseDTO:
        reservation = self.reservation_repository.find_by_phone_number(request.phone)
        if not reservation:
            return PreCheckInResponseDTO(
                success=False,
                message="Nenhuma reserva encontrada para este telefone.",
            )

        doc = (request.guest_document or "").replace(".", "").replace("-", "").strip()
        if len(doc) < 11:
            return PreCheckInResponseDTO(
                success=False,
                message="Informe um CPF válido (11 dígitos).",
            )

        try:
            reservation.complete_pre_checkin(
                guest_document=doc,
                estimated_arrival_time=request.estimated_arrival_time,
            )
            reservation.accept_terms()
            self.reservation_repository.save(reservation)
        except Exception as e:
            return PreCheckInResponseDTO(success=False, message=str(e))

        return PreCheckInResponseDTO(
            success=True,
            message=(
                "✅ Pré-check-in concluído!\n\n"
                "Seus dados foram registrados. Na chegada, apresente um documento com foto.\n"
                "Endereço: consulte a confirmação da reserva.\n\n"
                "Quando chegar, responda 'cheguei' para finalizar o check-in."
            ),
        )
