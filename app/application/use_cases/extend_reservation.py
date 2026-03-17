"""
Extend Reservation Use-Case - allows guests to extend their stay during hospitality.
"""
from datetime import date

from app.application.dto.extend_reservation_request_dto import ExtendReservationRequestDTO
from app.application.dto.extend_reservation_response_dto import ExtendReservationResponseDTO
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.repositories.reservation_repository import ReservationRepository
from app.domain.repositories.room_repository import RoomRepository
from app.domain import exceptions


class ExtendReservationUseCase:
    """Orchestrates reservation extension."""

    def __init__(
        self,
        reservation_repository: ReservationRepository,
        room_repository: RoomRepository,
    ):
        self.reservation_repository = reservation_repository
        self.room_repository = room_repository

    def prepare_extension(
        self, hotel_id: str, request_dto: ExtendReservationRequestDTO
    ) -> ExtendReservationResponseDTO:
        """
        Prepara extensão: retorna reserva ativa e data atual de saída.

        Returns:
            DTO com can_extend=True se houver reserva ativa (CONFIRMED ou CHECKED_IN)
        """
        reservation = self.reservation_repository.find_by_phone_number(
            request_dto.phone, hotel_id
        )
        if not reservation:
            return ExtendReservationResponseDTO(
                message="Reserva não encontrada para este telefone.",
                success=False,
            )

        if reservation.status not in (
            ReservationStatus.CONFIRMED,
            ReservationStatus.CHECKED_IN,
        ):
            return ExtendReservationResponseDTO(
                message=(
                    f"Reserva não pode ser estendida. "
                    f"Status atual: {reservation.status.name}."
                ),
                success=False,
                status=reservation.status.name,
            )

        if not reservation.stay_period or not reservation.room_number:
            return ExtendReservationResponseDTO(
                message="Reserva sem período ou quarto definido.",
                success=False,
            )

        current_checkout = reservation.stay_period.end
        summary = self._build_summary(reservation)
        return ExtendReservationResponseDTO(
            message=(
                f"Check-out atual: {current_checkout.strftime('%d/%m/%Y')}. "
                "Informe a nova data de saída (formato DD/MM/AAAA)."
            ),
            success=True,
            can_extend=True,
            current_checkout=current_checkout,
            summary=summary,
            status=reservation.status.name,
        )

    def extend(
        self, hotel_id: str, request_dto: ExtendReservationRequestDTO
    ) -> ExtendReservationResponseDTO:
        """
        Estende a reserva para nova data de check-out.

        Valida disponibilidade do quarto e chama reservation.extend_stay().
        """
        reservation = self.reservation_repository.find_by_phone_number(
            request_dto.phone, hotel_id
        )
        if not reservation:
            return ExtendReservationResponseDTO(
                message="Reserva não encontrada para este telefone.",
                success=False,
            )

        if not request_dto.new_checkout:
            return ExtendReservationResponseDTO(
                message="Data de check-out não informada.",
                success=False,
            )

        if not reservation.stay_period or not reservation.room_number:
            return ExtendReservationResponseDTO(
                message="Reserva sem período ou quarto definido.",
                success=False,
            )

        room = self.room_repository.get_by_number(hotel_id, reservation.room_number)
        if not room:
            return ExtendReservationResponseDTO(
                message="Quarto não encontrado.",
                success=False,
            )

        # Validar disponibilidade do quarto para o período estendido
        check_in = reservation.stay_period.start
        new_checkout = request_dto.new_checkout
        if not self.room_repository.is_available(
            hotel_id,
            reservation.room_number,
            check_in,
            new_checkout,
            exclude_reservation_id=reservation.id,
        ):
            return ExtendReservationResponseDTO(
                message=(
                    f"O quarto {reservation.room_number} não está disponível "
                    "para este período estendido. Tente outra data."
                ),
                success=False,
            )

        try:
            reservation.extend_stay(new_checkout, room.daily_rate)
            self.reservation_repository.save(reservation, hotel_id)
        except exceptions.InvalidExtendStayState as e:
            return ExtendReservationResponseDTO(
                message=str(e),
                success=False,
            )
        except exceptions.InvalidExtendStayDate as e:
            return ExtendReservationResponseDTO(
                message=str(e),
                success=False,
            )

        return ExtendReservationResponseDTO(
            message=(
                f"✅ Estadia estendida com sucesso! "
                f"Novo check-out: {new_checkout.strftime('%d/%m/%Y')}. "
                f"Total atualizado: R$ {reservation.total_amount:.2f}"
            ),
            success=True,
            can_extend=False,
        )

    @staticmethod
    def _build_summary(reservation) -> str:
        """Monta resumo da reserva para exibição."""
        lines = ["Resumo da reserva:"]
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
