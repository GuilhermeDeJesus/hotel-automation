from datetime import datetime
from typing import Optional
from app.domain.entities.payment.payment_status import PaymentStatus
from app.domain import exceptions


class Payment:
    """
    Entidade de Domínio: Payment
    
    Representa um pagamento de reserva.
    
    Regras:
    - Pagamento aprovado não pode ser alterado
    - Pagamento expirado invalida reserva
    - Pagamento pode ser estornado apenas se aprovado
    """
    
    def __init__(
        self,
        payment_id: str,
        reservation_id: str,
        hotel_id: str,
        amount: float,
        status: str = "PENDING",
        payment_method: Optional[str] = None,
        transaction_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        approved_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None
    ):
        self.id = payment_id
        self.reservation_id = reservation_id
        self.hotel_id = hotel_id
        self.amount = amount
        self.status = status
        self.payment_method = payment_method
        self.transaction_id = transaction_id
        self.created_at = created_at or datetime.now()
        self.approved_at = approved_at
        self.expires_at = expires_at
        
    def approve(self, transaction_id: Optional[str] = None) -> None:
        """
        Aprova o pagamento.
        
        Raises:
            InvalidPaymentState: Se pagamento não pode ser aprovado
        """
        if self.status != "PENDING":
            raise exceptions.InvalidPaymentState(
                f"Pagamento não pode ser aprovado. Status atual: {self.status}"
            )
        
        self.status = "APPROVED"
        self.approved_at = datetime.now()
        if transaction_id:
            self.transaction_id = transaction_id
    
    def reject(self, reason: Optional[str] = None) -> None:
        """Rejeita o pagamento."""
        if self.status == "PENDING":
            self.status = "REJECTED"
        
    def expire(self) -> None:
        """Marca pagamento como expirado."""
        if self.status == "PENDING":
            self.status = "EXPIRED"
    
    def refund(self) -> None:
        """
        Estorna o pagamento.
        
        Raises:
            InvalidPaymentState: Se pagamento não está aprovado
        """
        if self.status != "APPROVED":
            raise exceptions.InvalidPaymentState(
                "Apenas pagamentos aprovados podem ser estornados"
            )
        
        self.status = "REFUNDED"
    
    def is_approved(self) -> bool:
        """Verifica se pagamento foi aprovado."""
        return self.status == "APPROVED"
    
    def is_pending(self) -> bool:
        """Verifica se pagamento está pendente."""
        return self.status == "PENDING"
    
    def is_expired(self) -> bool:
        """Verifica se pagamento expirou."""
        return self.status == "EXPIRED" or (
            self.expires_at and datetime.now() > self.expires_at
        )
    
    def to_dict(self) -> dict:
        """Serializa o pagamento para dicionário."""
        return {
            "id": self.id,
            "reservation_id": self.reservation_id,
            "hotel_id": self.hotel_id,
            "amount": self.amount,
            "status": self.status,
            "payment_method": self.payment_method,
            "transaction_id": self.transaction_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }