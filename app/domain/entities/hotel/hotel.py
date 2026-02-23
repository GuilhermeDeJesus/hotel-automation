class Hotel:
    
    def __init__(self, hotel_id: str, name: str):
        self.id = hotel_id
        self.name = name
        self.checkin_policy = None
        
    def define_checkin_policy(self, policy):
        self.checkin_policy = policy
        
"""
📌 Hotel

        Define:
            horário de check-in
            horário de check-out
            política de cancelamento
"""