from enum import Enum

class PaymentStatus(Enum):
    
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    EXPIRED = "EXPIRED"