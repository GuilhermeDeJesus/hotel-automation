"""Seed a sample hotel record for development/testing."""
import uuid

from app.infrastructure.persistence.sql.database import SessionLocal, init_db
from app.infrastructure.persistence.sql.models import HotelModel, RoomModel


def seed_hotel() -> None:
    init_db()
    session = SessionLocal()

    existing = session.query(HotelModel).filter_by(is_active=True).first()
    if not existing:
        hotel = HotelModel(
            id=str(uuid.uuid4()),
            name="Hotel Automation",
            address="Avenida Central, 123, Brasilia - DF",
            contact_phone="+55 61 99999-0000",
            checkin_time="14:00",
            checkout_time="12:00",
            cancellation_policy="Cancelamento gratis ate 24h antes do check-in",
            pet_policy="Nao aceitamos pets",
            child_policy="Criancas ate 6 anos nao pagam",
            amenities="Wi-Fi, Piscina, Academia, Restaurante, Estacionamento",
            is_active=True,
        )
        session.add(hotel)

    room_seeds = [
        {"number": "101", "room_type": "SINGLE", "daily_rate": 220.0, "max_guests": 1},
        {"number": "102", "room_type": "DOUBLE", "daily_rate": 320.0, "max_guests": 2},
        {"number": "201", "room_type": "SUITE", "daily_rate": 520.0, "max_guests": 4},
    ]

    for room_data in room_seeds:
        room_exists = session.query(RoomModel).filter_by(number=room_data["number"]).first()
        if room_exists:
            continue

        room = RoomModel(
            id=str(uuid.uuid4()),
            number=room_data["number"],
            room_type=room_data["room_type"],
            daily_rate=room_data["daily_rate"],
            max_guests=room_data["max_guests"],
            status="AVAILABLE",
            is_active=True,
        )
        session.add(room)

    session.commit()
    session.close()
    print("Hotel e quartos seed criados com sucesso.")


if __name__ == "__main__":
    seed_hotel()
