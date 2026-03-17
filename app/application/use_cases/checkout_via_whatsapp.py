"""
Check-out via WhatsApp Use Case - orchestrates guest check-out.
"""
from app.application.dto.checkout_request_dto import CheckoutRequestDTO
from app.application.dto.checkout_response_dto import CheckoutResponseDTO
from app.domain import exceptions
from app.domain.repositories.reservation_repository import ReservationRepository


class CheckoutViaWhatsAppUseCase:
    """Orquestra o check-out do hóspede via WhatsApp."""

    def __init__(self, reservation_repository: ReservationRepository):
        self.reservation_repository = reservation_repository

    def execute(self, hotel_id: str, request_dto: CheckoutRequestDTO) -> CheckoutResponseDTO:
        reservation = self.reservation_repository.find_by_phone_number(request_dto.phone, hotel_id)
        if not reservation:
            return CheckoutResponseDTO(
                message="Nenhuma reserva encontrada.",
                success=False,
            )

        try:
            reservation.check_out()
            self.reservation_repository.save(reservation, hotel_id)
            return CheckoutResponseDTO(
                message="Check-out realizado com sucesso!",
                success=True,
            )
        except exceptions.InvalidCheckOutState as e:
            return CheckoutResponseDTO(
                message=str(e),
                success=False,
                error=str(e),
            )
