"""
Payment Repository - interface para persistência de pagamentos.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities.payment.payment import Payment


class PaymentRepository(ABC):
    """Interface para repositório de pagamentos."""

    @abstractmethod
    def save(self, hotel_id: str, payment: Payment) -> None:
        """Persiste ou atualiza um pagamento para um hotel."""
        pass

    @abstractmethod
    def find_by_id(self, hotel_id: str, payment_id: str) -> Optional[Payment]:
        """Retorna pagamento por ID e hotel ou None."""
        pass

    @abstractmethod
    def find_by_transaction_id(self, hotel_id: str, transaction_id: str) -> Optional[Payment]:
        """Retorna pagamento por transaction_id e hotel (ex: Stripe session_id)."""
        pass

    @abstractmethod
    def list_payments(
        self,
        hotel_id: str,
        reservation_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Payment]:
        """Lista pagamentos de um hotel com filtros opcionais."""
        pass

    @abstractmethod
    def find_by_id_global(self, payment_id: str) -> Optional[Payment]:
        """Retorna pagamento por ID sem filtro de hotel (uso especial em webhooks)."""
        pass
