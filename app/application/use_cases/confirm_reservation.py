"""
Confirm Reservation Use-Case - guides a guest to confirm a reservation.
"""
from app.application.dto.confirm_reservation_request_dto import ConfirmReservationRequestDTO
from app.application.dto.confirm_reservation_response_dto import ConfirmReservationResponseDTO
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.repositories.reservation_repository import ReservationRepository


class ConfirmReservationUseCase:
    """Orchestrates reservation confirmation."""

    def __init__(self, reservation_repository: ReservationRepository):
        self.reservation_repository = reservation_repository

    def prepare_confirmation(self, request_dto: ConfirmReservationRequestDTO) -> ConfirmReservationResponseDTO:
        reservation = self.reservation_repository.find_by_phone_number(request_dto.phone)
        if not reservation:
            return ConfirmReservationResponseDTO(
                message="Reserva nao encontrada para este telefone.",
                success=False,
            )

        if reservation.status in [
            ReservationStatus.CANCELLED,
            ReservationStatus.NO_SHOW,
            ReservationStatus.CHECKED_OUT,
        ]:
            return ConfirmReservationResponseDTO(
                message=f"Reserva nao pode ser confirmada. Status atual: {reservation.status.name}.",
                success=False,
                status=reservation.status.name,
            )

        if reservation.status == ReservationStatus.CONFIRMED:
            return ConfirmReservationResponseDTO(
                message="Reserva ja esta confirmada.",
                success=True,
                can_confirm=False,
                status=reservation.status.name,
            )

        summary = self._build_summary(reservation)
        return ConfirmReservationResponseDTO(
            message="Deseja confirmar esta reserva? Responda com SIM ou NAO.",
            success=True,
            can_confirm=True,
            summary=summary,
            status=reservation.status.name,
        )

    def confirm(self, request_dto: ConfirmReservationRequestDTO) -> ConfirmReservationResponseDTO:
        reservation = self.reservation_repository.find_by_phone_number(request_dto.phone)
        if not reservation:
            return ConfirmReservationResponseDTO(
                message="Reserva nao encontrada para este telefone.",
                success=False,
            )

        if reservation.status in [
            ReservationStatus.CANCELLED,
            ReservationStatus.NO_SHOW,
            ReservationStatus.CHECKED_OUT,
        ]:
            return ConfirmReservationResponseDTO(
                message=f"Reserva nao pode ser confirmada. Status atual: {reservation.status.name}.",
                success=False,
                status=reservation.status.name,
            )

        if reservation.status == ReservationStatus.CONFIRMED:
            return ConfirmReservationResponseDTO(
                message="Reserva ja estava confirmada.",
                success=True,
                can_confirm=False,
                status=reservation.status.name,
            )

        reservation.confirm()
        self.reservation_repository.save(reservation)

        return ConfirmReservationResponseDTO(
            message="Reserva confirmada com sucesso.",
            success=True,
            can_confirm=False,
            status=reservation.status.name,
        )

    def get_formatted_summary(self, reservation) -> str:
        """Retorna resumo bem formatado com emojis e detalhes."""
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📋 CONFIRMAÇÃO DE RESERVA",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]

        if reservation.guest_name:
            lines.append(f"👤 Hóspede: {reservation.guest_name}")

        if reservation.room_number:
            lines.append(f"🏠 Quarto: {reservation.room_number}")

        if reservation.stay_period:
            lines.append(
                f"📅 Check-in: {reservation.stay_period.start.strftime('%d/%m/%Y')}"
            )
            lines.append(
                f"📅 Check-out: {reservation.stay_period.end.strftime('%d/%m/%Y')}"
            )
            num_nights = reservation.stay_period.number_of_nights()
            lines.append(f"🌙 Duração: {num_nights} noite(s)")

        if reservation.total_amount:
            daily_rate = (
                reservation.total_amount / reservation.stay_period.number_of_nights()
                if reservation.stay_period and reservation.stay_period.number_of_nights() > 0
                else 0
            )
            if daily_rate > 0:
                lines.append(f"💰 Diária: R$ {daily_rate:.2f}")
            lines.append(f"📊 Total: R$ {reservation.total_amount:.2f}")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        return "\n".join(lines)

    @staticmethod
    def _build_summary(reservation) -> str:
        """Alias compatível para uso anterior."""
        lines: list[str] = ["Resumo da reserva:"]
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
