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
    url = os.getenv("DATABASE_URL")
    if not url:
        url = "sqlite:///:memory:"
    engine = create_engine(url)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_save():
    Session = setup_test_db()
    session = Session()
    
    repo = ReservationRepositorySQL(session)
    
    reservation = Reservation(
        reservation_id="",
        guest_name="Guilherme",
        guest_phone=PhoneNumber("61998493256"),
        status=ReservationStatus.CONFIRMED
    )
    
    repo.save(reservation)
    assert reservation.id != ""

def test_save_and_find_reservation():
    Session = setup_test_db()
    session = Session()
    repo = ReservationRepositorySQL(session)
    # Use a unique phone number for this test to avoid conflicts with previous runs
    phone = "98765432102"

    # Create reservation with CONFIRMED status (before check-in)
    reservation = Reservation(
        reservation_id="",
        guest_name="Test Guest",
        guest_phone=PhoneNumber(phone),
        status=ReservationStatus.CONFIRMED,
    )

    # save and then retrieve
    repo.save(reservation)
    assert reservation.id != ""  # ID should be assigned after save

    found = repo.find_by_phone_number(phone)
    assert found is not None
    assert found.id == reservation.id
    assert str(found.guest_phone) == phone
    assert found.status == ReservationStatus.CONFIRMED

    # Perform check-in (changes status from CONFIRMED to CHECKED_IN)
    reservation.check_in()
    repo.save(reservation)

    # Verify check-in was successful
    updated = repo.find_by_phone_number(phone)
    assert updated is not None
    assert updated.status == ReservationStatus.CHECKED_IN


def test_save_inserts_multiple_phones():
    Session = setup_test_db()
    session = Session()
    repo = ReservationRepositorySQL(session)
    # Use unique phone numbers to avoid conflicts
    phone1, phone2 = "11111111111", "22222222222"

    r1 = Reservation("", "Guest One", PhoneNumber(phone1), ReservationStatus.CONFIRMED)
    repo.save(r1)
    assert r1.id != ""

    r2 = Reservation("", "Guest Two", PhoneNumber(phone2), ReservationStatus.CONFIRMED)
    repo.save(r2)
    assert r2.id != "" and r2.id != r1.id

    # both reservations must be retrievable by their own phone numbers
    assert repo.find_by_phone_number(phone1).id == r1.id
    assert repo.find_by_phone_number(phone2).id == r2.id


def test_save_updates_latest_reservation_for_same_phone():
    Session = setup_test_db()
    session = Session()
    repo = ReservationRepositorySQL(session)

    phone = "33333333333"
    older = Reservation("", "Guest", PhoneNumber(phone), ReservationStatus.PENDING)
    repo.save(older)

    latest = Reservation("", "Guest", PhoneNumber(phone), ReservationStatus.PENDING)
    repo.save(latest)

    latest.confirm()
    repo.save(latest)

    found = repo.find_by_phone_number(phone)
    assert found is not None
    assert found.id == latest.id
    assert found.status == ReservationStatus.CONFIRMED


if __name__ == "__main__":
    pytest.main([__file__])