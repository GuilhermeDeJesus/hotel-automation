"""Confirm payment manually (Fase 0 - comprovante recebido)."""
from __future__ import annotations

from app.domain import exceptions
from app.domain.repositories.payment_repository import PaymentRepository
from app.domain.repositories.reservation_repository import ReservationRepository


class ConfirmPaymentManualUseCase:
    def __init__(
        self,
        payment_repository: PaymentRepository,
        reservation_repository: ReservationRepository,
    ):
        self.payment_repository = payment_repository
        self.reservation_repository = reservation_repository

    def execute(self, hotel_id: str, payment_id: str, transaction_id: str | None = None) -> dict:
        """
        Approve payment manually (hotel confirmed receipt).

        Returns:
            {"success": True, "message": "..."} or {"success": False, "error": "..."}
        """
        payment = self.payment_repository.find_by_id(hotel_id, payment_id)
        if not payment:
            return {"success": False, "error": "Pagamento não encontrado."}

        try:
            payment.approve(transaction_id=transaction_id)
            self.payment_repository.save(hotel_id, payment)

            # Optionally confirm reservation when payment is approved
            reservation = self.reservation_repository.find_by_id(payment.reservation_id, hotel_id)
            if reservation:
                if reservation.status.name == "PENDING":
                    reservation.confirm()
                    self.reservation_repository.save(reservation, hotel_id)
                guest_phone = str(reservation.guest_phone)
            else:
                guest_phone = None
            return {
                "success": True,
                "message": "Pagamento confirmado com sucesso.",
                "guest_phone": guest_phone,
            }
        except exceptions.InvalidPaymentState as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}
