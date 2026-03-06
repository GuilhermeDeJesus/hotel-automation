"""
Cancel Reservation Use-Case - guides a guest to cancel a reservation.
"""
from app.application.dto.cancel_reservation_request_dto import CancelReservationRequestDTO
from app.application.dto.cancel_reservation_response_dto import CancelReservationResponseDTO
from app.domain import exceptions
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.repositories.reservation_repository import ReservationRepository


class CancelReservationUseCase:
    """Orchestrates reservation cancellation."""

    def __init__(self, reservation_repository: ReservationRepository):
        self.reservation_repository = reservation_repository

    def prepare_cancellation(
        self, request_dto: CancelReservationRequestDTO
    ) -> CancelReservationResponseDTO:
        reservation = self.reservation_repository.find_by_phone_number(request_dto.phone)
        if not reservation:
            return CancelReservationResponseDTO(
                message="Reserva não encontrada para este telefone.",
                success=False,
            )

        if reservation.status in [
            ReservationStatus.CHECKED_IN,
            ReservationStatus.CHECKED_OUT,
        ]:
            return CancelReservationResponseDTO(
                message="Não é possível cancelar reserva após check-in.",
                success=False,
                status=reservation.status.name,
            )

        if reservation.status == ReservationStatus.CANCELLED:
            return CancelReservationResponseDTO(
                message="Reserva já está cancelada.",
                success=True,
                can_cancel=False,
                status=reservation.status.name,
            )

        if reservation.status == ReservationStatus.NO_SHOW:
            return CancelReservationResponseDTO(
                message="Reserva já foi marcada como no-show.",
                success=False,
                status=reservation.status.name,
            )

        summary = self._build_summary(reservation)
        return CancelReservationResponseDTO(
            message="Deseja realmente cancelar esta reserva? Responda com SIM ou NÃO.",
            success=True,
            can_cancel=True,
            summary=summary,
            status=reservation.status.name,
        )

    def cancel(self, request_dto: CancelReservationRequestDTO) -> CancelReservationResponseDTO:
        reservation = self.reservation_repository.find_by_phone_number(request_dto.phone)
        if not reservation:
            return CancelReservationResponseDTO(
                message="Reserva não encontrada para este telefone.",
                success=False,
            )

        try:
            reservation.cancel()
            self.reservation_repository.save(reservation)
            return CancelReservationResponseDTO(
                message="Reserva cancelada com sucesso.",
                success=True,
                can_cancel=False,
                status=reservation.status.name,
            )
        except exceptions.InvalidCancellationState as e:
            return CancelReservationResponseDTO(
                message=str(e),
                success=False,
                status=reservation.status.name,
            )

    @staticmethod
    def _build_summary(reservation) -> str:
        lines: list[str] = ["Resumo da reserva a cancelar:"]
        if reservation.guest_name:
            lines.append(f"- Nome: {reservation.guest_name}")
        lines.append(f"- Status: {reservation.status.name}")
        if reservation.stay_period:
            lines.append(
                f"- Check-in: {reservation.stay_period.start.strftime('%d/%m/%Y')}"
            )
            lines.append(
                f"- Check-out: {reservation.stay_period.end.strftime('%d/%m/%Y')}"
            )
        if reservation.room_number:
            lines.append(f"- Quarto: {reservation.room_number}")
        if reservation.total_amount:
            lines.append(f"- Total: R$ {reservation.total_amount:.2f}")
        return "\n".join(lines)
