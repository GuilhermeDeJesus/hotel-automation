"""
Payment Repository - interface para persistência de pagamentos.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities.payment.payment import Payment


class PaymentRepository(ABC):
    """Interface para repositório de pagamentos."""

    @abstractmethod
    def save(self, payment: Payment) -> None:
        """Persiste ou atualiza um pagamento."""
        pass

    @abstractmethod
    def find_by_id(self, payment_id: str) -> Optional[Payment]:
        """Retorna pagamento por ID ou None."""
        pass

    @abstractmethod
    def find_by_transaction_id(self, transaction_id: str) -> Optional[Payment]:
        """Retorna pagamento por transaction_id (ex: Stripe session_id)."""
        pass

    @abstractmethod
    def list_payments(
        self,
        reservation_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Payment]:
        """Lista pagamentos com filtros opcionais."""
        pass
