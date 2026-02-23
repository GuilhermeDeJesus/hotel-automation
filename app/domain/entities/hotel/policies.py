class CheckinPolicy:
    def __init__(self, allowed_hour: int):
        self.allowed_hour = allowed_hour

    def is_allowed(self, hour: int) -> bool:
        return hour >= self.allowed_hour