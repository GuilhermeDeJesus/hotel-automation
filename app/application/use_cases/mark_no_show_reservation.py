"""Mark a single reservation as no-show."""
from __future__ import annotations

from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.repositories.reservation_repository import ReservationRepository


class MarkNoShowReservationUseCase:
    def __init__(self, reservation_repository: ReservationRepository):
        self.reservation_repository = reservation_repository

    def execute(self, reservation_id: str) -> dict:
        """
        Mark reservation as NO_SHOW.

        Returns:
            {"success": True, "message": "..."} or {"success": False, "error": "..."}
        """
        reservation = self.reservation_repository.find_by_id(reservation_id)
        if not reservation:
            return {"success": False, "error": "Reserva não encontrada."}

        if reservation.status != ReservationStatus.CONFIRMED:
            return {
                "success": False,
                "error": f"Só é possível marcar no-show em reservas confirmadas. Status atual: {reservation.status.name}.",
            }

        reservation.mark_as_no_show()
        self.reservation_repository.save(reservation)
        return {"success": True, "message": "Reserva marcada como no-show."}
