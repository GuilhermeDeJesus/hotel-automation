class PhoneNumber:
    #Constructor da classe PhoneNumber, que recebe um número de telefone como string e valida seu formato.
    def __init__(self, number: str):
        if not number or not number.isdigit() or len(number) < 10:
            raise ValueError("Invalid phone number format")
        self.number = number

    def __str__(self):
        return self.number
    
    
    