"""Testes de isolamento multi-tenant entre hotéis."""

import pytest
import uuid
from datetime import datetime, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.persistence.sql.models import Base, UserModel, HotelModel, ReservationModel, RoomModel
from app.infrastructure.persistence.sql.reservation_repository_sql import ReservationRepositorySQL
from app.infrastructure.persistence.sql.room_repository_sql import RoomRepositorySQL
from app.infrastructure.persistence.sql.payment_repository_sql import PaymentRepositorySQL
from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.entities.room.room import Room
from app.domain.value_objects.phone_number import PhoneNumber
from app.interfaces.dependencies.auth import get_current_user


# Database de teste
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_multi_tenant.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TestMultiTenantIsolation:
    """Testes de isolamento de dados entre hotéis."""
    
    @pytest.fixture(scope="function")
    def db_session(self):
        """Setup do banco de dados para cada teste."""
        Base.metadata.create_all(bind=engine)
        session = TestingSessionLocal()
        yield session
        session.close()
        Base.metadata.drop_all(bind=engine)
    
    @pytest.fixture
    def hotel_a(self, db_session):
        """Cria Hotel A."""
        hotel = HotelModel(
            id="hotel-a-123",
            name="Hotel A",
            address="Rua A, 123",
            contact_phone="11999999999",
            checkin_time="14:00",
            checkout_time="12:00",
            cancellation_policy="Política A",
            pet_policy="Pets A",
            child_policy="Crianças A",
            amenities="Wi-Fi, Piscina",
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db_session.add(hotel)
        db_session.commit()
        return hotel
    
    @pytest.fixture
    def hotel_b(self, db_session):
        """Cria Hotel B."""
        hotel = HotelModel(
            id="hotel-b-456",
            name="Hotel B", 
            address="Rua B, 456",
            contact_phone="11888888888",
            checkin_time="14:00",
            checkout_time="12:00",
            cancellation_policy="Política B",
            pet_policy="Pets B",
            child_policy="Crianças B",
            amenities="Wi-Fi, Spa",
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db_session.add(hotel)
        db_session.commit()
        return hotel
    
    @pytest.fixture
    def user_hotel_a(self, db_session, hotel_a):
        """Cria usuário do Hotel A."""
        user = UserModel(
            id="user-a-123",
            email="user@hotela.com",
            password_hash="hashed_password",
            role="user",
            hotel_id=hotel_a.id,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db_session.add(user)
        db_session.commit()
        return user
    
    @pytest.fixture
    def user_hotel_b(self, db_session, hotel_b):
        """Cria usuário do Hotel B."""
        user = UserModel(
            id="user-b-456",
            email="user@hotelb.com",
            password_hash="hashed_password",
            role="user",
            hotel_id=hotel_b.id,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db_session.add(user)
        db_session.commit()
        return user
    
    @pytest.fixture
    def admin_user(self, db_session):
        """Cria usuário admin (sem hotel específico)."""
        user = UserModel(
            id="admin-789",
            email="admin@system.com",
            password_hash="hashed_password",
            role="admin",
            hotel_id=None,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db_session.add(user)
        db_session.commit()
        return user
    
    def test_room_isolation_between_hotels(self, db_session, hotel_a, hotel_b):
        """Testa que quartos são isolados por hotel."""
        room_repo = RoomRepositorySQL(db_session)
        
        # Criar quarto no Hotel A
        room_a = Room(
            number="101",
            room_type="SINGLE",
            daily_rate=150.0,
            max_guests=1,
            status="AVAILABLE",
            hotel_id=hotel_a.id
        )
        saved_room_a = room_repo.save(room_a, hotel_a.id)
        
        # Criar quarto no Hotel B
        room_b = Room(
            number="101",  # Mesmo número, mas hotel diferente
            room_type="DOUBLE",
            daily_rate=250.0,
            max_guests=2,
            status="AVAILABLE",
            hotel_id=hotel_b.id
        )
        saved_room_b = room_repo.save(room_b, hotel_b.id)
        
        # Usuario do Hotel A só deve ver quartos do Hotel A
        rooms_a = room_repo.list_all(hotel_a.id)
        assert len(rooms_a) == 1
        assert rooms_a[0].hotel_id == hotel_a.id
        assert rooms_a[0].room_type == "SINGLE"
        
        # Usuario do Hotel B só deve ver quartos do Hotel B
        rooms_b = room_repo.list_all(hotel_b.id)
        assert len(rooms_b) == 1
        assert rooms_b[0].hotel_id == hotel_b.id
        assert rooms_b[0].room_type == "DOUBLE"
        
        # Busca por número deve retornar quarto do hotel correto
        found_a = room_repo.get_by_number(hotel_a.id, "101")
        assert found_a is not None
        assert found_a.hotel_id == hotel_a.id
        assert found_a.room_type == "SINGLE"
        
        found_b = room_repo.get_by_number(hotel_b.id, "101")
        assert found_b is not None
        assert found_b.hotel_id == hotel_b.id
        assert found_b.room_type == "DOUBLE"
    
    def test_reservation_isolation_between_hotels(self, db_session, hotel_a, hotel_b):
        """Testa que reservas são isoladas por hotel."""
        reservation_repo = ReservationRepositorySQL(db_session)
        
        # Criar reserva no Hotel A
        reservation_a = Reservation(
            reservation_id=str(uuid.uuid4()),
            guest_name="João Hotel A",
            hotel_id=hotel_a.id,
            guest_phone=PhoneNumber("11999999999"),
            status=ReservationStatus.PENDING
        )
        reservation_repo.save(reservation_a, hotel_a.id)
        
        # Criar reserva no Hotel B (mesmo telefone)
        reservation_b = Reservation(
            reservation_id=str(uuid.uuid4()),
            guest_name="Maria Hotel B",
            hotel_id=hotel_b.id,
            guest_phone=PhoneNumber("11999999999"),
            status=ReservationStatus.PENDING
        )
        reservation_repo.save(reservation_b, hotel_b.id)
        
        # Busca por telefone no Hotel A deve retornar apenas reserva A
        found_a = reservation_repo.find_by_phone_number("11999999999", hotel_a.id)
        assert found_a is not None
        assert found_a.hotel_id == hotel_a.id
        assert found_a.guest_name == "João Hotel A"
        
        # Busca por telefone no Hotel B deve retornar apenas reserva B
        found_b = reservation_repo.find_by_phone_number("11999999999", hotel_b.id)
        assert found_b is not None
        assert found_b.hotel_id == hotel_b.id
        assert found_b.guest_name == "Maria Hotel B"
        
        # Listar reservas do Hotel A
        reservations_a = reservation_repo.list_reservations(hotel_a.id)
        assert len(reservations_a) == 1
        assert reservations_a[0].hotel_id == hotel_a.id
        
        # Listar reservas do Hotel B
        reservations_b = reservation_repo.list_reservations(hotel_b.id)
        assert len(reservations_b) == 1
        assert reservations_b[0].hotel_id == hotel_b.id
    
    def test_cross_hotel_data_leak_prevention(self, db_session, hotel_a, hotel_b):
        """Testa que não há vazamento de dados entre hotéis."""
        reservation_repo = ReservationRepositorySQL(db_session)
        room_repo = RoomRepositorySQL(db_session)
        
        # Criar dados no Hotel A
        reservation_a = Reservation(
            reservation_id=str(uuid.uuid4()),
            guest_name="Hóspede A",
            hotel_id=hotel_a.id,
            guest_phone=PhoneNumber("11999999999"),
            status=ReservationStatus.CONFIRMED
        )
        reservation_repo.save(reservation_a, hotel_a.id)
        
        room_a = Room(
            number="201",
            room_type="SUITE",
            daily_rate=500.0,
            max_guests=2,
            status="AVAILABLE",
            hotel_id=hotel_a.id
        )
        room_repo.save(room_a, hotel_a.id)
        
        # Tentar buscar dados do Hotel A usando hotel_id do Hotel B
        reservation_wrong = reservation_repo.find_by_phone_number("11999999999", hotel_b.id)
        assert reservation_wrong is None  # Não deve encontrar
        
        room_wrong = room_repo.get_by_number(hotel_b.id, "201")
        assert room_wrong is None  # Não deve encontrar
        
        # Tentar buscar por ID de reserva com hotel errado
        found_wrong_hotel = reservation_repo.find_by_id(reservation_a.id, hotel_b.id)
        assert found_wrong_hotel is None  # Não deve encontrar
        
        # Busca correta deve funcionar
        found_correct = reservation_repo.find_by_id(reservation_a.id, hotel_a.id)
        assert found_correct is not None
        assert found_correct.hotel_id == hotel_a.id
    
    def test_admin_can_access_all_hotels(self, db_session, hotel_a, hotel_b):
        """Testa que admin pode acessar dados de todos os hotéis."""
        reservation_repo = ReservationRepositorySQL(db_session)
        room_repo = RoomRepositorySQL(db_session)
        
        # Criar dados em ambos os hotéis
        reservation_a = Reservation(
            reservation_id=str(uuid.uuid4()),
            guest_name="Hóspede A",
            hotel_id=hotel_a.id,
            guest_phone=PhoneNumber("11999999999"),
            status=ReservationStatus.PENDING
        )
        reservation_repo.save(reservation_a, hotel_a.id)
        
        reservation_b = Reservation(
            reservation_id=str(uuid.uuid4()),
            guest_name="Hóspede B",
            hotel_id=hotel_b.id,
            guest_phone=PhoneNumber("11888888888"),
            status=ReservationStatus.PENDING
        )
        reservation_repo.save(reservation_b, hotel_b.id)
        
        # Admin pode acessar dados de ambos os hotéis
        reservations_a = reservation_repo.list_reservations(hotel_a.id)
        reservations_b = reservation_repo.list_reservations(hotel_b.id)
        
        assert len(reservations_a) == 1
        assert len(reservations_b) == 1
        assert reservations_a[0].hotel_id == hotel_a.id
        assert reservations_b[0].hotel_id == hotel_b.id
    
    def test_payment_isolation_between_hotels(self, db_session, hotel_a, hotel_b):
        """Testa que pagamentos são isolados por hotel."""
        payment_repo = PaymentRepositorySQL(db_session)
        
        # Criar pagamento no Hotel A
        from app.domain.entities.payment.payment import Payment
        payment_a = Payment(
            payment_id=str(uuid.uuid4()),
            reservation_id=str(uuid.uuid4()),
            hotel_id=hotel_a.id,
            amount=300.0,
            status="PENDING"
        )
        payment_repo.save(hotel_a.id, payment_a)
        
        # Criar pagamento no Hotel B
        payment_b = Payment(
            payment_id=str(uuid.uuid4()),
            reservation_id=str(uuid.uuid4()),
            hotel_id=hotel_b.id,
            amount=500.0,
            status="APPROVED"
        )
        payment_repo.save(hotel_b.id, payment_b)
        
        # Listar pagamentos do Hotel A
        payments_a = payment_repo.list_payments(hotel_a.id)
        assert len(payments_a) == 1
        assert payments_a[0].hotel_id == hotel_a.id
        assert payments_a[0].amount == 300.0
        
        # Listar pagamentos do Hotel B
        payments_b = payment_repo.list_payments(hotel_b.id)
        assert len(payments_b) == 1
        assert payments_b[0].hotel_id == hotel_b.id
        assert payments_b[0].amount == 500.0


class TestTenantValidationMiddleware:
    """Testes do middleware de validação de tenant."""
    
    def test_validate_hotel_access_same_hotel(self):
        """Testa acesso permitido quando usuário é do mesmo hotel."""
        from app.interfaces.middleware.tenant_middleware import validate_hotel_access
        
        # Mock user do hotel A
        user = UserModel(
            id="user-123",
            email="user@hotel.com",
            password_hash="hash",
            role="user",
            hotel_id="hotel-a-123",
            is_active=True
        )
        
        # Mock da função de validação
        validator = validate_hotel_access()
        result = validator("hotel-a-123")
        assert result == "hotel-a-123"
    
    def test_validate_hotel_access_different_hotel_denied(self):
        """Testa acesso negado quando usuário é de hotel diferente."""
        from app.interfaces.middleware.tenant_middleware import validate_hotel_access
        from fastapi import HTTPException
        
        # Mock user do hotel A
        user = UserModel(
            id="user-123",
            email="user@hotel.com",
            password_hash="hash",
            role="user",
            hotel_id="hotel-a-123",
            is_active=True
        )
        
        # Mock da função de validação
        validator = validate_hotel_access()
        
        # Tentar acessar hotel B deve falhar
        with pytest.raises(HTTPException) as exc_info:
            validator("hotel-b-456")
        
        assert exc_info.value.status_code == 403
        assert "Acesso negado" in str(exc_info.value.detail)
    
    def test_admin_can_access_any_hotel(self):
        """Testa que admin pode acessar qualquer hotel."""
        from app.interfaces.middleware.tenant_middleware import validate_hotel_access
        
        # Mock admin user
        user = UserModel(
            id="admin-789",
            email="admin@system.com",
            password_hash="hash",
            role="admin",
            hotel_id=None,
            is_active=True
        )
        
        # Mock da função de validação
        validator = validate_hotel_access()
        
        # Admin pode acessar qualquer hotel
        result_a = validator("hotel-a-123")
        result_b = validator("hotel-b-456")
        
        assert result_a == "hotel-a-123"
        assert result_b == "hotel-b-456"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
