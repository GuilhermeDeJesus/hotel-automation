import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.persistence.sql.database import Base
from app.infrastructure.persistence.sql.reservation_repository_sql import ReservationRepositorySQL
from app.domain.entities.reservation.reservation import Reservation
from app.domain.value_objects.phone_number import PhoneNumber
from app.domain.entities.reservation.reservation_status import ReservationStatus

from dotenv import load_dotenv

load_dotenv()

def setup_test_db():
    """Usa TEST_DATABASE_URL ou DATABASE_URL ou sqlite em memória."""
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or "sqlite:///:memory:"
    connect_args = {"check_same_thread": False} if "sqlite" in url else {}
    engine = create_engine(url, connect_args=connect_args)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_save_multi_tenant_inserts_with_hotel_id():
    Session = setup_test_db()
    session = Session()
    
    repo = ReservationRepositorySQL(session)
    hotel_id = "hotel-a"
    reservation = Reservation(
        reservation_id="",
        guest_name="Guilherme",
        guest_phone=PhoneNumber("61998493256"),
        status=ReservationStatus.CONFIRMED,
        hotel_id=hotel_id,
    )
    
    repo.save(reservation, hotel_id)
    assert reservation.id != ""

def test_save_and_find_reservation_scoped_by_hotel():
    Session = setup_test_db()
    session = Session()
    repo = ReservationRepositorySQL(session)
    hotel_id = "hotel-a"
    # Use a unique phone number for this test to avoid conflicts with previous runs
    phone = "98765432102"

    # Create reservation with CONFIRMED status (before check-in)
    reservation = Reservation(
        reservation_id="",
        guest_name="Test Guest",
        guest_phone=PhoneNumber(phone),
        status=ReservationStatus.CONFIRMED,
        hotel_id=hotel_id,
    )

    # save and then retrieve
    repo.save(reservation, hotel_id)
    assert reservation.id != ""  # ID should be assigned after save

    found = repo.find_by_phone_number(phone, hotel_id)
    assert found is not None
    assert found.id == reservation.id
    assert str(found.guest_phone) == phone
    assert found.status == ReservationStatus.CONFIRMED

    # Perform check-in (changes status from CONFIRMED to CHECKED_IN)
    reservation.check_in()
    repo.save(reservation, hotel_id)

    # Verify check-in was successful
    updated = repo.find_by_phone_number(phone, hotel_id)
    assert updated is not None
    assert updated.status == ReservationStatus.CHECKED_IN


def test_save_inserts_multiple_phones_per_hotel():
    Session = setup_test_db()
    session = Session()
    repo = ReservationRepositorySQL(session)
    hotel_id = "hotel-a"
    # Use unique phone numbers to avoid conflicts
    phone1, phone2 = "11111111111", "22222222222"

    r1 = Reservation("", "Guest One", hotel_id, PhoneNumber(phone1), ReservationStatus.CONFIRMED)
    repo.save(r1, hotel_id)
    assert r1.id != ""

    r2 = Reservation("", "Guest Two", hotel_id, PhoneNumber(phone2), ReservationStatus.CONFIRMED)
    repo.save(r2, hotel_id)
    assert r2.id != "" and r2.id != r1.id

    # both reservations must be retrievable by their own phone numbers
    assert repo.find_by_phone_number(phone1, hotel_id).id == r1.id
    assert repo.find_by_phone_number(phone2, hotel_id).id == r2.id


def test_save_updates_latest_reservation_for_same_phone_per_hotel():
    Session = setup_test_db()
    session = Session()
    repo = ReservationRepositorySQL(session)
    hotel_id = "hotel-a"

    phone = "33333333333"
    older = Reservation("", "Guest", hotel_id, PhoneNumber(phone), ReservationStatus.PENDING)
    repo.save(older, hotel_id)

    latest = Reservation("", "Guest", hotel_id, PhoneNumber(phone), ReservationStatus.PENDING)
    repo.save(latest, hotel_id)

    latest.confirm()
    repo.save(latest, hotel_id)

    found = repo.find_by_phone_number(phone, hotel_id)
    assert found is not None
    assert found.id == latest.id
    assert found.status == ReservationStatus.CONFIRMED


def test_find_by_phone_number_normalizes_input_format_and_respects_hotel():
    Session = setup_test_db()
    session = Session()
    repo = ReservationRepositorySQL(session)
    hotel_id = "hotel-a"

    phone_digits = "556198776092"
    reservation = Reservation(
        reservation_id="",
        guest_name="Format Guest",
        guest_phone=PhoneNumber(phone_digits),
        status=ReservationStatus.PENDING,
        hotel_id=hotel_id,
    )
    repo.save(reservation, hotel_id)

    found = repo.find_by_phone_number("+55 (61) 98776-092", hotel_id)

    assert found is not None
    assert str(found.guest_phone) == phone_digits


if __name__ == "__main__":
    pytest.main([__file__])