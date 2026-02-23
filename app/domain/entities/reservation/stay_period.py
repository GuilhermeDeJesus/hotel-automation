from datetime import date

class StayPeriod:
    
    def __init__(self, start: date, end: date):
        if self.start >= self.end:
            raise Exception("Período inválido")
        self.start = start
        self.end = end
    
    def is_checkin_allowed(self, today: date) -> bool:
        return today >= self.start