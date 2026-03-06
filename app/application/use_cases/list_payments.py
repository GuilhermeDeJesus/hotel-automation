"""List payments with optional filters."""
from __future__ import annotations

from typing import Any, Optional

from app.domain.repositories.payment_repository import PaymentRepository


class ListPaymentsUseCase:
    def __init__(self, payment_repository: PaymentRepository):
        self.payment_repository = payment_repository

    def execute(
        self,
        reservation_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        payments = self.payment_repository.list_payments(
            reservation_id=reservation_id,
            status=status,
            limit=limit,
        )
        return [self._to_dict(p) for p in payments]

    @staticmethod
    def _to_dict(p) -> dict[str, Any]:
        return {
            "id": p.id,
            "reservation_id": p.reservation_id,
            "amount": p.amount,
            "status": p.status,
            "payment_method": p.payment_method,
            "transaction_id": p.transaction_id,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "approved_at": p.approved_at.isoformat() if p.approved_at else None,
            "expires_at": p.expires_at.isoformat() if p.expires_at else None,
        }
