from app.domain.entities.payment.payment_status import PaymentStatus

class Payment:
    
    def __init__(self, payment_id: str, reservation_id: str):
        self.id = payment_id
        self.reservation_id = reservation_id
        self.status = "PENDING"
        
    def approved(self):
        if self.status != "PENDING":
            raise Exception("Pagamento não pode ser aprovado")
        self.status = "APPROVED"
        
    def expired(self):
        self.status = "EXPIRED"
        
"""
📌 Pagamento

        Pagamento aprovado:
            não pode ser alterado

        Pagamento expirado:
            invalida reserva

        Pagamento reage a evento (não é chamado direto)
"""