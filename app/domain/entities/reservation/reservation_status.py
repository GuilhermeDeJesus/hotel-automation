from enum import Enum

class ReservationStatus(Enum):
    """Status possíveis de uma reserva"""
    PENDING = "PENDING"              # Aguardando confirmação
    CONFIRMED = "CONFIRMED"          # Reserva confirmada
    CHECKED_IN = "CHECKED_IN"        # Hóspede realizou check-in
    CHECKED_OUT = "CHECKED_OUT"      # Hóspede realizou check-out
    CANCELLED = "CANCELLED"          # Reserva cancelada
    NO_SHOW = "NO_SHOW"              # Hóspede não compareceu