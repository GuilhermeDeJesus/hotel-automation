"""
Payment Recovery Service - 6.7 Recuperação de pagamento.

Se pagamento falhar ou expirar: envia novo link com prazo.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from app.domain.repositories.payment_repository import PaymentRepository
from app.domain.repositories.reservation_repository import ReservationRepository
from app.domain.services.payment_provider import PaymentProvider


@dataclass
class PaymentRecoveryItem:
    reservation_id: str
    phone: str
    amount: float
    payment_id: str
    new_checkout_url: Optional[str]


class PaymentRecoveryService:
    """6.7 Gera novos links de pagamento para cobranças expiradas."""

    def __init__(
        self,
        payment_repository: PaymentRepository,
        reservation_repository: ReservationRepository,
        payment_provider: PaymentProvider,
    ):
        self.payment_repository = payment_repository
        self.reservation_repository = reservation_repository
        self.payment_provider = payment_provider

    def get_recovery_links(self) -> List[PaymentRecoveryItem]:
        """
        Busca pagamentos PENDING/EXPIRED e gera novo link.
        Requer método find_expired_pending no PaymentRepository.
        """
        items = []
        if hasattr(self.payment_repository, "find_expired_or_pending_for_recovery"):
            payments = self.payment_repository.find_expired_or_pending_for_recovery()
        else:
            payments = []

        for payment in payments:
            if not payment.is_pending() and payment.status != "EXPIRED":
                continue
            reservation = self.reservation_repository.find_by_id(payment.reservation_id)
            if not reservation or reservation.status.name != "PENDING":
                continue

            amount_cents = int(payment.amount * 100)
            result = self.payment_provider.create_checkout_link(
                reservation_id=payment.reservation_id,
                amount_cents=amount_cents,
                description=f"Reserva - Recuperação #{payment.reservation_id[:8]}",
                currency="brl",
                payment_id=payment.id,
            )
            url = result[0] if result else None
            items.append(PaymentRecoveryItem(
                reservation_id=payment.reservation_id,
                phone=str(reservation.guest_phone),
                amount=payment.amount,
                payment_id=payment.id,
                new_checkout_url=url,
            ))
        return items
