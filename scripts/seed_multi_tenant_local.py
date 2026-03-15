"""Seed multi-tenant data for development/testing (Docker version)."""
import uuid
import os
import sys
from datetime import datetime
from passlib.hash import bcrypt

# Adicionar diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar para uso local fora do Docker
os.environ['DATABASE_URL'] = 'postgresql://postgres:postgres@localhost:5432/hotel'

from app.infrastructure.persistence.sql.database import SessionLocal, init_db
from app.infrastructure.persistence.sql.models import (
    HotelModel, RoomModel, UserModel, CustomerModel, ReservationModel, PaymentModel
)


def seed_multi_tenant_data() -> None:
    """Cria dados multi-tenant para desenvolvimento/teste."""
    try:
        init_db()
        session = SessionLocal()
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {str(e)}")
        print("\n💡 Solução:")
        print("1. Verifique se o PostgreSQL está rodando na porta 5432")
        print("2. Ou use Docker: docker compose up -d")
        print("3. Ou configure DATABASE_URL para seu banco")
        return

    print("🏨 Criando dados multi-tenant...")
    
    # 1. Verificar hotéis existentes ou criar novos
    hotels_data = [
        {
            "id": "d03dbe9a-1812-46dd-8e8c-c8fedace48a0",  # UUID real do Hotel Kelly Pontes
            "name": "Hotel Kelly Pontes",
            "address": "Avenida Beira Mar, 500, Rio de Janeiro - RJ",
            "contact_phone": "+55 21 99999-1111",
            "checkin_time": "14:00",
            "checkout_time": "12:00",
            "cancellation_policy": "Cancelamento grátis até 48h antes do check-in",
            "pet_policy": "Pets pequenos bem-vindos (taxa de R$ 50/dia)",
            "child_policy": "Crianças até 5 anos não pagam",
            "amenities": "Wi-Fi Ultra, Piscina Rooftop, Spa, Academia 24h, Restaurante Gastronômico, Valet Parking",
            "is_active": True,
            "requires_payment_for_confirmation": False,
            "allows_reservation_without_payment": True,
        },
        {
            "id": "temp-hotel",  # Usar hotel temporário existente
            "name": "Temp Hotel",
            "address": "Rua Temp, 123, São Paulo - SP",
            "contact_phone": "+55 11 99999-0000",
            "checkin_time": "14:00",
            "checkout_time": "12:00",
            "cancellation_policy": "Política Temp",
            "pet_policy": "Pets Temp",
            "child_policy": "Crianças Temp",
            "amenities": "Wi-Fi, Piscina",
            "is_active": True,
            "requires_payment_for_confirmation": False,
            "allows_reservation_without_payment": True,
        },
        {
            "id": "test-hotel-123",  # Usar hotel de teste existente
            "name": "Hotel Teste",
            "address": "Rua Teste, 123, Brasilia - DF",
            "contact_phone": "+55 61 99999-0000",
            "checkin_time": "14:00",
            "checkout_time": "12:00",
            "cancellation_policy": "Política teste",
            "pet_policy": "Pets teste",
            "child_policy": "Crianças teste",
            "amenities": "Wi-Fi, Piscina",
            "is_active": True,
            "requires_payment_for_confirmation": False,
            "allows_reservation_without_payment": True,
        }
    ]
    
    created_hotels = []
    for hotel_data in hotels_data:
        existing = session.query(HotelModel).filter_by(id=hotel_data["id"]).first()
        if not existing:
            hotel = HotelModel(
                id=hotel_data["id"],
                name=hotel_data["name"],
                address=hotel_data["address"],
                contact_phone=hotel_data["contact_phone"],
                checkin_time=hotel_data["checkin_time"],
                checkout_time=hotel_data["checkout_time"],
                cancellation_policy=hotel_data["cancellation_policy"],
                pet_policy=hotel_data["pet_policy"],
                child_policy=hotel_data["child_policy"],
                amenities=hotel_data["amenities"],
                is_active=hotel_data["is_active"],
                requires_payment_for_confirmation=hotel_data["requires_payment_for_confirmation"],
                allows_reservation_without_payment=hotel_data["allows_reservation_without_payment"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            session.add(hotel)
            created_hotels.append(hotel_data)
            print(f"  ✅ Hotel criado: {hotel_data['name']}")
        else:
            created_hotels.append(hotel_data)
            print(f"  ⏭️  Hotel já existe: {hotel_data['name']}")
    
    # 2. Criar quartos para cada hotel
    rooms_by_hotel = {
        "d03dbe9a-1812-46dd-8e8c-c8fedace48a0": [
            {"number": "801", "room_type": "SINGLE", "daily_rate": 280.0, "max_guests": 1},
            {"number": "802", "room_type": "SINGLE", "daily_rate": 280.0, "max_guests": 1},
            {"number": "803", "room_type": "DOUBLE", "daily_rate": 380.0, "max_guests": 2},
            {"number": "804", "room_type": "DOUBLE", "daily_rate": 380.0, "max_guests": 2},
            {"number": "901", "room_type": "SUITE", "daily_rate": 680.0, "max_guests": 4},
        ],
        "temp-hotel": [
            {"number": "301", "room_type": "SINGLE", "daily_rate": 220.0, "max_guests": 1},
            {"number": "302", "room_type": "DOUBLE", "daily_rate": 320.0, "max_guests": 2},
            {"number": "303", "room_type": "DOUBLE", "daily_rate": 320.0, "max_guests": 2},
            {"number": "304", "room_type": "SUITE", "daily_rate": 520.0, "max_guests": 4},
        ],
        "test-hotel-123": [
            {"number": "501", "room_type": "SINGLE", "daily_rate": 180.0, "max_guests": 1},
            {"number": "502", "room_type": "SINGLE", "daily_rate": 180.0, "max_guests": 1},
            {"number": "503", "room_type": "DOUBLE", "daily_rate": 250.0, "max_guests": 2},
            {"number": "504", "room_type": "DOUBLE", "daily_rate": 250.0, "max_guests": 2},
            {"number": "505", "room_type": "EXECUTIVE", "daily_rate": 450.0, "max_guests": 3},
        ]
    }
    
    for hotel_id, rooms_data in rooms_by_hotel.items():
        for room_data in rooms_data:
            existing = session.query(RoomModel).filter_by(
                hotel_id=hotel_id, 
                number=room_data["number"]
            ).first()
            if not existing:
                room = RoomModel(
                    id=str(uuid.uuid4()),
                    hotel_id=hotel_id,
                    number=room_data["number"],
                    room_type=room_data["room_type"],
                    daily_rate=room_data["daily_rate"],
                    max_guests=room_data["max_guests"],
                    status="AVAILABLE",
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                session.add(room)
        
        hotel_name = next(h["name"] for h in hotels_data if h["id"] == hotel_id)
        print(f"  ✅ Quartos criados para {hotel_name}: {len(rooms_data)} quartos")
    
    # 3. Criar usuários associados a hotéis específicos
    users_data = [
        # Hotel Kelly Pontes
        {
            "id": "user-kelly-admin",
            "email": "admin@kelly.com",
            "password": "admin123",
            "role": "admin",
            "hotel_id": "d03dbe9a-1812-46dd-8e8c-c8fedace48a0",
            "name": "Administrador Kelly"
        },
        {
            "id": "user-kelly-manager",
            "email": "manager@kelly.com", 
            "password": "manager123",
            "role": "manager",
            "hotel_id": "d03dbe9a-1812-46dd-8e8c-c8fedace48a0",
            "name": "Gerente Kelly"
        },
        {
            "id": "user-kelly-staff1",
            "email": "reception@kelly.com",
            "password": "staff123",
            "role": "staff", 
            "hotel_id": "d03dbe9a-1812-46dd-8e8c-c8fedace48a0",
            "name": "Recepcionista Kelly"
        },
        
        # Temp Hotel
        {
            "id": "user-temp-admin",
            "email": "admin@temp.com",
            "password": "admin123",
            "role": "admin",
            "hotel_id": "temp-hotel",
            "name": "Administrador Temp"
        },
        {
            "id": "user-temp-manager",
            "email": "manager@temp.com",
            "password": "manager123", 
            "role": "manager",
            "hotel_id": "temp-hotel",
            "name": "Gerente Temp"
        },
        
        # Test Hotel
        {
            "id": "user-test-admin",
            "email": "admin@test.com",
            "password": "admin123",
            "role": "admin",
            "hotel_id": "test-hotel-123",
            "name": "Administrador Test"
        },
        
        # Super Admin (sem hotel específico)
        {
            "id": "super-admin-001",
            "email": "superadmin@system.com",
            "password": "superadmin123",
            "role": "admin",
            "hotel_id": None,  # Super admin pode acessar todos os hotéis
            "name": "Super Administrador"
        }
    ]
    
    for user_data in users_data:
        existing = session.query(UserModel).filter_by(email=user_data["email"]).first()
        if not existing:
            user = UserModel(
                id=user_data["id"],
                email=user_data["email"],
                password_hash=bcrypt.hash(user_data["password"]),
                role=user_data["role"],
                hotel_id=user_data["hotel_id"],
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            session.add(user)
            
            hotel_name = "Super Admin" if user_data["hotel_id"] is None else \
                        next(h["name"] for h in hotels_data if h["id"] == user_data["hotel_id"])
            print(f"  ✅ Usuário criado: {user_data['name']} ({user_data['role']}) - {hotel_name}")
        else:
            print(f"  ⏭️  Usuário já existe: {user_data['email']}")
    
    # 4. Criar clientes de exemplo para cada hotel
    customers_by_hotel = {
        "d03dbe9a-1812-46dd-8e8c-c8fedace48a0": [
            {"name": "João Silva", "phone": "+55 21 98888-1111", "email": "joao@email.com", "document": "12345678900"},
            {"name": "Maria Santos", "phone": "+55 21 98888-2222", "email": "maria@email.com", "document": "98765432100"},
            {"name": "Pedro Costa", "phone": "+55 21 98888-3333", "email": "pedro@email.com", "document": "11122233344"},
        ],
        "temp-hotel": [
            {"name": "Carlos Oliveira", "phone": "+55 11 97777-1111", "email": "carlos@email.com", "document": "55566677788"},
            {"name": "Ana Ferreira", "phone": "+55 11 97777-2222", "email": "ana@email.com", "document": "99988877766"},
        ],
        "test-hotel-123": [
            {"name": "Roberto Lima", "phone": "+55 61 96666-1111", "email": "roberto@email.com", "document": "44433322211"},
            {"name": "Lucia Pereira", "phone": "+55 61 96666-2222", "email": "lucia@email.com", "document": "77788899900"},
            {"name": "Marcos Almeida", "phone": "+55 61 96666-3333", "email": "marcos@email.com", "document": "33322211100"},
        ]
    }
    
    for hotel_id, customers_data in customers_by_hotel.items():
        for customer_data in customers_data:
            existing = session.query(CustomerModel).filter_by(
                hotel_id=hotel_id,
                document=customer_data["document"]
            ).first()
            if not existing:
                customer = CustomerModel(
                    id=str(uuid.uuid4()),
                    hotel_id=hotel_id,
                    name=customer_data["name"],
                    phone=customer_data["phone"],
                    email=customer_data["email"],
                    document=customer_data["document"],
                    status="ACTIVE",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                session.add(customer)
        
        hotel_name = next(h["name"] for h in hotels_data if h["id"] == hotel_id)
        print(f"  ✅ Clientes criados para {hotel_name}: {len(customers_data)} clientes")
    
    # 5. Criar algumas reservas de exemplo
    sample_reservations = [
        # Hotel Kelly Pontes
        {
            "id": "res-kelly-001",
            "hotel_id": "d03dbe9a-1812-46dd-8e8c-c8fedace48a0",
            "guest_name": "João Silva",
            "guest_phone": "+55 21 98888-1111",
            "room_number": "901",
            "status": "CONFIRMED",
            "total_amount": 1360.0,  # 2 noites SUITE
        },
        {
            "id": "res-kelly-002", 
            "hotel_id": "d03dbe9a-1812-46dd-8e8c-c8fedace48a0",
            "guest_name": "Maria Santos",
            "guest_phone": "+55 21 98888-2222",
            "room_number": "803",
            "status": "PENDING",
            "total_amount": 760.0,  # 2 noites DOUBLE
        },
        
        # Temp Hotel
        {
            "id": "res-temp-001",
            "hotel_id": "temp-hotel", 
            "guest_name": "Carlos Oliveira",
            "guest_phone": "+55 11 97777-1111",
            "room_number": "304",
            "status": "CHECKED_IN",
            "total_amount": 1560.0,  # 3 noites SUITE
        },
        
        # Test Hotel
        {
            "id": "res-test-001",
            "hotel_id": "test-hotel-123",
            "guest_name": "Roberto Lima", 
            "guest_phone": "+55 61 96666-1111",
            "room_number": "505",
            "status": "CONFIRMED",
            "total_amount": 1350.0,  # 3 noites EXECUTIVE
        }
    ]
    
    for res_data in sample_reservations:
        existing = session.query(ReservationModel).filter_by(id=res_data["id"]).first()
        if not existing:
            reservation = ReservationModel(
                id=res_data["id"],
                hotel_id=res_data["hotel_id"],
                guest_name=res_data["guest_name"],
                guest_phone=res_data["guest_phone"],
                room_number=res_data["room_number"],
                status=res_data["status"],
                total_amount=res_data["total_amount"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            session.add(reservation)
        
        hotel_name = next(h["name"] for h in hotels_data if h["id"] == res_data["hotel_id"])
        print(f"  ✅ Reserva criada: {res_data['guest_name']} - {hotel_name}")
    
    try:
        session.commit()
        session.close()
        
        print("\n" + "=" * 60)
        print("🎉 DADOS MULTI-TENANT CRIADOS COM SUCESSO!")
        print("=" * 60)
        print(f"📊 Resumo:")
        print(f"  • Hotéis: {len(hotels_data)}")
        print(f"  • Usuários: {len(users_data)}")
        print(f"  • Quartos totais: {sum(len(rooms) for rooms in rooms_by_hotel.values())}")
        print(f"  • Clientes: {sum(len(customers) for customers in customers_by_hotel.values())}")
        print(f"  • Reservas: {len(sample_reservations)}")
        print("\n🔑 Credenciais de teste:")
        print("  • Super Admin: superadmin@system.com / superadmin123")
        print("  • Admin Paradise: admin@paradise.com / admin123")
        print("  • Admin Montanha: admin@montanha.com / admin123")
        print("  • Admin Urbano: admin@urbano.com / admin123")
        print("\n📝 Para testar isolamento:")
        print("  1. Faça login como admin@paradise.com")
        print("  2. Tente acessar dados do hotel-montanha-002 (deve ser bloqueado)")
        print("  3. Faça login como superadmin@system.com")
        print("  4. Acesse dados de qualquer hotel (deve permitir)")
        
    except Exception as e:
        print(f"❌ Erro ao commitar dados: {str(e)}")
        session.rollback()


if __name__ == "__main__":
    seed_multi_tenant_data()
