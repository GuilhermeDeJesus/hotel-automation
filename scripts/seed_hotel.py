"""Seed a sample hotel record for development/testing."""
import uuid

from app.infrastructure.persistence.sql.database import SessionLocal, init_db
from app.infrastructure.persistence.sql.models import HotelModel


def seed_hotel() -> None:
    init_db()
    session = SessionLocal()

    existing = session.query(HotelModel).filter_by(is_active=True).first()
    if existing:
        print("Hotel ativo ja existe, pulando seed.")
        session.close()
        return

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
    session.commit()
    session.close()
    print("Hotel seed criado com sucesso.")


if __name__ == "__main__":
    seed_hotel()
