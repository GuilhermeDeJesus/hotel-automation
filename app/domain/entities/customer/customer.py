from app.domain.entities.customer.customer_status import CustomerStatus

class Customer:
    
    def __init__(self, customer_id: str, name: str):
        self.id = customer_id
        self.name = name
        self.status = "ACTIVE"
        
    def block(self):
        self.status = "BLOCKED"
        
    def can_checkin(self) -> bool:
        return self.status == "ACTIVE"
    
    
"""
📌Cliente

    Cliente bloqueado:
        não faz check-in

    Documento inválido:
        impede hospedagem
"""