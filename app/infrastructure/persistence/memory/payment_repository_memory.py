"""Payment Repository em memória para testes."""
from datetime import datetime
from typing import List, Optional

from app.domain.entities.payment.payment import Payment
from app.domain.repositories.payment_repository import PaymentRepository


class PaymentRepositoryMemory(PaymentRepository):
    """Implementação em memória do repositório de pagamentos."""

    def __init__(self):
        self._payments: dict[str, Payment] = {}

    def save(self, payment: Payment) -> None:
        self._payments[payment.id] = payment

    def find_by_id(self, payment_id: str) -> Optional[Payment]:
        return self._payments.get(payment_id)

    def find_by_transaction_id(self, transaction_id: str) -> Optional[Payment]:
        for p in self._payments.values():
            if p.transaction_id == transaction_id:
                return p
        return None

    def list_payments(
        self,
        reservation_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Payment]:
        result = []
        for p in self._payments.values():
            if reservation_id and str(p.reservation_id) != str(reservation_id):
                continue
            if status and p.status.upper() != status.upper():
                continue
            result.append(p)
        result.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
        return result[:limit]
