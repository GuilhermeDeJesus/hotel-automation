import uuid
from app.infrastructure.persistence.sql.database import SessionLocal, init_db
from app.infrastructure.persistence.sql.models import HotelModel

def seed_hotels():
    init_db()
    session = SessionLocal()
    hotels = [
        {
            "id": "hotel-paradise-001",
            "name": "Hotel Paradise",
            "address": "Rua das Flores, 100, Rio de Janeiro - RJ",
            "contact_phone": "+55 21 99999-0001",
            "checkin_time": "14:00",
            "checkout_time": "12:00",
            "cancellation_policy": "Cancelamento grátis até 24h antes do check-in",
            "pet_policy": "Aceita pets de pequeno porte",
            "child_policy": "Crianças até 7 anos não pagam",
            "amenities": "Wi-Fi, Piscina, Restaurante, Estacionamento",
            "is_active": True,
        },
        {
            "id": "hotel-montanha-002",
            "name": "Hotel Montanha",
            "address": "Avenida das Montanhas, 200, Belo Horizonte - MG",
            "contact_phone": "+55 31 99999-0002",
            "checkin_time": "15:00",
            "checkout_time": "11:00",
            "cancellation_policy": "Cancelamento grátis até 48h antes do check-in",
            "pet_policy": "Não aceita pets",
            "child_policy": "Crianças até 5 anos não pagam",
            "amenities": "Wi-Fi, Academia, Restaurante, Estacionamento",
            "is_active": True,
        },
        {
            "id": "hotel-urbano-003",
            "name": "Hotel Urbano",
            "address": "Rua Central, 300, São Paulo - SP",
            "contact_phone": "+55 11 99999-0003",
            "checkin_time": "13:00",
            "checkout_time": "12:00",
            "cancellation_policy": "Cancelamento grátis até 24h antes do check-in",
            "pet_policy": "Aceita pets",
            "child_policy": "Crianças até 6 anos não pagam",
            "amenities": "Wi-Fi, Restaurante, Estacionamento",
            "is_active": True,
        },
    ]
    for h in hotels:
        if not session.query(HotelModel).filter_by(id=h["id"]).first():
            hotel = HotelModel(**h)
            session.add(hotel)
    session.commit()
    session.close()
    print("Hotéis seed criados com sucesso.")

if __name__ == "__main__":
    seed_hotels()
