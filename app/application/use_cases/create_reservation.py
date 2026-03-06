"""
Create Reservation Use-Case - creates a new reservation from collected data.
"""
import uuid

from app.application.dto.create_reservation_request_dto import CreateReservationRequestDTO
from app.application.dto.create_reservation_response_dto import CreateReservationResponseDTO
from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.entities.reservation.stay_period import StayPeriod
from app.domain.value_objects.phone_number import PhoneNumber
from app.domain.repositories.reservation_repository import ReservationRepository
from app.domain.repositories.room_repository import RoomRepository


class CreateReservationUseCase:
    """Orchestrates reservation creation."""

    def __init__(
        self,
        reservation_repository: ReservationRepository,
        room_repository: RoomRepository,
    ):
        self.reservation_repository = reservation_repository
        self.room_repository = room_repository

    def check_availability(self, check_in, check_out):
        """Retorna quartos disponíveis para o período."""
        return self.room_repository.find_available(check_in, check_out)

    def create(self, request_dto: CreateReservationRequestDTO) -> CreateReservationResponseDTO:
        """Cria reserva PENDING e persiste."""
        room = self.room_repository.get_by_number(request_dto.room_number)
        if not room:
            return CreateReservationResponseDTO(
                message=f"Quarto {request_dto.room_number} não encontrado.",
                success=False,
            )

        available = self.room_repository.is_available(
            request_dto.room_number,
            request_dto.check_in,
            request_dto.check_out,
        )
        if not available:
            return CreateReservationResponseDTO(
                message=f"Quarto {request_dto.room_number} não está disponível para este período.",
                success=False,
            )

        try:
            stay_period = StayPeriod(request_dto.check_in, request_dto.check_out)
        except ValueError as e:
            return CreateReservationResponseDTO(
                message=str(e),
                success=False,
            )

        num_nights = stay_period.number_of_nights()
        total_amount = room.daily_rate * num_nights

        reservation = Reservation(
            reservation_id=str(uuid.uuid4()),
            guest_name=request_dto.guest_name.strip(),
            guest_phone=PhoneNumber(request_dto.phone),
            status=ReservationStatus.PENDING,
            stay_period=stay_period,
            room_number=request_dto.room_number,
            total_amount=total_amount,
        )

        self.reservation_repository.save(reservation)

        return CreateReservationResponseDTO(
            message="Reserva criada com sucesso! Envie 'confirmar reserva' para confirmar.",
            success=True,
            reservation_id=reservation.id,
        )
