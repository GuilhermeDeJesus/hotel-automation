from datetime import date, timedelta
from typing import Optional


class StayPeriod:
    """
    Value Object: Período de Estadia
    
    Representa o período (check-in e check-out) de uma reserva.
    
    Regras:
    - Data de início deve ser antes da data de fim
    - Data de início não pode ser no passado (ao criar nova reserva)
    - Mínimo 1 dia de estadia
    """
    
    def __init__(self, start: date, end: date, allow_past: bool = False):
        # Validações
        if start >= end:
            raise ValueError(
                f"Data de início ({start}) deve ser anterior à data de fim ({end})"
            )
        
        if not allow_past and start < date.today():
            raise ValueError(
                f"Data de início ({start}) não pode ser no passado"
            )
        
        self.start = start
        self.end = end
    
    def is_checkin_allowed(self, today: Optional[date] = None) -> bool:
        """
        Verifica se o check-in é permitido na data fornecida.
        
        Args:
            today: Data a verificar (padrão: hoje)
        
        Returns:
            True se check-in é permitido
        """
        if today is None:
            today = date.today()
        
        # Permite check-in no dia ou depois
        return today >= self.start
    
    def is_checkout_allowed(self, today: Optional[date] = None) -> bool:
        """
        Verifica se o check-out é permitido na data fornecida.
        
        Args:
            today: Data a verificar (padrão: hoje)
        
        Returns:
            True se check-out é permitido
        """
        if today is None:
            today = date.today()
        
        # Permite check-out no dia ou antes
        return today <= self.end
    
    def is_active(self, today: Optional[date] = None) -> bool:
        """Verifica se o período está ativo (dentro das datas)."""
        if today is None:
            today = date.today()
        
        return self.start <= today <= self.end
    
    def number_of_nights(self) -> int:
        """Retorna o número de noites da estadia."""
        return (self.end - self.start).days
    
    def overlaps_with(self, other: 'StayPeriod') -> bool:
        """Verifica se há sobreposição com outro período."""
        return self.start < other.end and other.start < self.end
    
    def __str__(self) -> str:
        """Representação em string do período."""
        return f"{self.start} até {self.end} ({self.number_of_nights()} noites)"
    
    def __eq__(self, other: object) -> bool:
        """Compara dois períodos."""
        if not isinstance(other, StayPeriod):
            return False
        return self.start == other.start and self.end == other.end