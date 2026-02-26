from datetime import datetime
from typing import Optional
from app.domain.entities.customer.customer_status import CustomerStatus
from app.domain.value_objects.phone_number import PhoneNumber


class Customer:
    """
    Entidade de Domínio: Customer (Cliente/Hóspede)
    
    Representa um cliente do hotel.
    
    Regras:
    - Cliente bloqueado não pode fazer check-in
    - Cliente precisa ter documento válido
    - Cliente pode ter histórico de reservas
    """
    
    def __init__(
        self, 
        customer_id: str, 
        name: str,
        phone: Optional[PhoneNumber] = None,
        email: Optional[str] = None,
        document: Optional[str] = None,
        status: str = "ACTIVE",
        created_at: Optional[datetime] = None
    ):
        self.id = customer_id
        self.name = name
        self.phone = phone
        self.email = email
        self.document = document
        self.status = status
        self.created_at = created_at or datetime.now()
        
    def block(self, reason: Optional[str] = None) -> None:
        """Bloqueia o cliente."""
        self.status = "BLOCKED"
        # Aqui poderia salvar o motivo do bloqueio
        
    def unblock(self) -> None:
        """Desbloqueia o cliente."""
        if self.status == "BLOCKED":
            self.status = "ACTIVE"
        
    def can_checkin(self) -> bool:
        """Verifica se o cliente pode fazer check-in."""
        return self.status == "ACTIVE"
    
    def is_active(self) -> bool:
        """Verifica se o cliente está ativo."""
        return self.status == "ACTIVE"
    
    def has_valid_document(self) -> bool:
        """Verifica se o cliente tem documento válido."""
        return self.document is not None and len(self.document) > 0
    
    def to_dict(self) -> dict:
        """Serializa o cliente para dicionário."""
        return {
            "id": self.id,
            "name": self.name,
            "phone": str(self.phone) if self.phone else None,
            "email": self.email,
            "document": self.document,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }