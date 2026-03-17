"""Seed multi-tenant data for development/testing. Padrão: Docker."""
import uuid
import os
import sys
from pathlib import Path
from datetime import datetime
from passlib.hash import bcrypt

# Adicionar diretório raiz ao PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Carrega .env (DATABASE_URL para Docker)
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from app.infrastructure.persistence.sql.database import SessionLocal, init_db
from app.infrastructure.persistence.sql.models import (
    HotelModel, RoomModel, UserModel, CustomerModel, ReservationModel, PaymentModel
)


def seed_multi_tenant_data() -> None:
    """Cria dados multi-tenant para desenvolvimento/teste."""
    init_db()
    session = SessionLocal()

    print("🏨 Criando dados multi-tenant...")
    
    # 1. Criar múltiplos hotéis
    hotels_data = [
        {
            "id": "hotel-paradise-001",
            "name": "Hotel Paradise Premium",
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
            "id": "hotel-montanha-002", 
            "name": "Mountain Lodge Resort & Spa",
            "address": "Estrada da Montanha, km 12, Campos do Jordão - SP",
            "contact_phone": "+55 12 99999-2222",
            "checkin_time": "15:00",
            "checkout_time": "11:00",
            "cancellation_policy": "Cancelamento grátis até 72h antes do check-in",
            "pet_policy": "Não aceitamos pets (exceto cães-guia)",
            "child_policy": "Crianças até 12 anos têm 50% de desconto",
            "amenities": "Wi-Fi, Piscina Aquecida, Sauna, Lareira, Lounge, Churrasqueira, Trilhas",
            "is_active": True,
            "requires_payment_for_confirmation": True,
            "allows_reservation_without_payment": False,
        },
        {
            "id": "hotel-urbano-003",
            "name": "Hotel Urbano Business",
            "address": "Rua das Flores, 200, São Paulo - SP",
            "contact_phone": "+55 11 99999-3333",
            "checkin_time": "13:00",
            "checkout_time": "12:00",
            "cancellation_policy": "Cancelamento grátis até 24h antes do check-in",
            "pet_policy": "Aceitamos pequenos animais (taxa de R$ 30/dia)",
            "child_policy": "Crianças até 7 anos não pagam",
            "amenities": "Wi-Fi High-Speed, Business Center, Sala de Reuniões, Fitness, Café 24h",
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
    
    # Commit hotéis antes de criar dependências (FK)
    session.commit()

    # 2. Criar quartos para cada hotel
    rooms_by_hotel = {
        "hotel-paradise-001": [
            {"number": "101", "room_type": "SINGLE", "daily_rate": 280.0, "max_guests": 1},
            {"number": "102", "room_type": "SINGLE", "daily_rate": 280.0, "max_guests": 1},
            {"number": "103", "room_type": "DOUBLE", "daily_rate": 380.0, "max_guests": 2},
            {"number": "104", "room_type": "DOUBLE", "daily_rate": 380.0, "max_guests": 2},
            {"number": "201", "room_type": "SUITE", "daily_rate": 680.0, "max_guests": 4},
            {"number": "202", "room_type": "SUITE", "daily_rate": 680.0, "max_guests": 4},
            {"number": "301", "room_type": "PRESIDENTIAL", "daily_rate": 1280.0, "max_guests": 6},
        ],
        "hotel-montanha-002": [
            {"number": "A1", "room_type": "SINGLE", "daily_rate": 220.0, "max_guests": 1},
            {"number": "A2", "room_type": "DOUBLE", "daily_rate": 320.0, "max_guests": 2},
            {"number": "A3", "room_type": "DOUBLE", "daily_rate": 320.0, "max_guests": 2},
            {"number": "B1", "room_type": "SUITE", "daily_rate": 520.0, "max_guests": 4},
            {"number": "B2", "room_type": "SUITE", "daily_rate": 520.0, "max_guests": 4},
            {"number": "C1", "room_type": "CHALE", "daily_rate": 820.0, "max_guests": 5},
        ],
        "hotel-urbano-003": [
            {"number": "501", "room_type": "SINGLE", "daily_rate": 180.0, "max_guests": 1},
            {"number": "502", "room_type": "SINGLE", "daily_rate": 180.0, "max_guests": 1},
            {"number": "503", "room_type": "DOUBLE", "daily_rate": 250.0, "max_guests": 2},
            {"number": "504", "room_type": "DOUBLE", "daily_rate": 250.0, "max_guests": 2},
            {"number": "601", "room_type": "EXECUTIVE", "daily_rate": 450.0, "max_guests": 3},
            {"number": "602", "room_type": "EXECUTIVE", "daily_rate": 450.0, "max_guests": 3},
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
    
    # Commit quartos antes de criar usuários
    session.commit()

    # 3. Criar usuários associados a hotéis específicos
    users_data = [
        # Hotel Paradise
        {
            "id": "user-paradise-admin",
            "email": "admin@paradise.com",
            "password": "admin123",
            "role": "admin",
            "hotel_id": "hotel-paradise-001",
            "name": "Administrador Paradise"
        },
        {
            "id": "user-paradise-manager",
            "email": "manager@paradise.com", 
            "password": "manager123",
            "role": "manager",
            "hotel_id": "hotel-paradise-001",
            "name": "Gerente Paradise"
        },
        {
            "id": "user-paradise-staff1",
            "email": "reception@paradise.com",
            "password": "staff123",
            "role": "staff", 
            "hotel_id": "hotel-paradise-001",
            "name": "Recepcionista Paradise"
        },
        {
            "id": "user-paradise-staff2",
            "email": "housekeeping@paradise.com",
            "password": "staff123",
            "role": "staff",
            "hotel_id": "hotel-paradise-001", 
            "name": "Camareira Paradise"
        },
        
        # Hotel Montanha
        {
            "id": "user-montanha-admin",
            "email": "admin@montanha.com",
            "password": "admin123",
            "role": "admin",
            "hotel_id": "hotel-montanha-002",
            "name": "Administrador Montanha"
        },
        {
            "id": "user-montanha-manager",
            "email": "manager@montanha.com",
            "password": "manager123", 
            "role": "manager",
            "hotel_id": "hotel-montanha-002",
            "name": "Gerente Montanha"
        },
        {
            "id": "user-montanha-staff1",
            "email": "reception@montanha.com",
            "password": "staff123",
            "role": "staff",
            "hotel_id": "hotel-montanha-002",
            "name": "Recepcionista Montanha"
        },
        
        # Hotel Urbano
        {
            "id": "user-urbano-admin",
            "email": "admin@urbano.com",
            "password": "admin123",
            "role": "admin",
            "hotel_id": "hotel-urbano-003",
            "name": "Administrador Urbano"
        },
        {
            "id": "user-urbano-manager", 
            "email": "manager@urbano.com",
            "password": "manager123",
            "role": "manager",
            "hotel_id": "hotel-urbano-003",
            "name": "Gerente Urbano"
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

    # Commit usuários antes de criar clientes
    session.commit()

    # 4. Criar clientes de exemplo para cada hotel
    customers_by_hotel = {
        "hotel-paradise-001": [
            {"name": "João Silva", "phone": "+55 21 98888-1111", "email": "joao@email.com", "document": "12345678900"},
            {"name": "Maria Santos", "phone": "+55 21 98888-2222", "email": "maria@email.com", "document": "98765432100"},
            {"name": "Pedro Costa", "phone": "+55 21 98888-3333", "email": "pedro@email.com", "document": "11122233344"},
        ],
        "hotel-montanha-002": [
            {"name": "Carlos Oliveira", "phone": "+55 12 97777-1111", "email": "carlos@email.com", "document": "55566677788"},
            {"name": "Ana Ferreira", "phone": "+55 12 97777-2222", "email": "ana@email.com", "document": "99988877766"},
        ],
        "hotel-urbano-003": [
            {"name": "Roberto Lima", "phone": "+55 11 96666-1111", "email": "roberto@email.com", "document": "44433322211"},
            {"name": "Lucia Pereira", "phone": "+55 11 96666-2222", "email": "lucia@email.com", "document": "77788899900"},
            {"name": "Marcos Almeida", "phone": "+55 11 96666-3333", "email": "marcos@email.com", "document": "33322211100"},
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
        # Hotel Paradise
        {
            "id": "res-paradise-001",
            "hotel_id": "hotel-paradise-001",
            "guest_name": "João Silva",
            "guest_phone": "+55 21 98888-1111",
            "room_number": "201",
            "status": "CONFIRMED",
            "total_amount": 1360.0,  # 2 noites SUITE
        },
        {
            "id": "res-paradise-002", 
            "hotel_id": "hotel-paradise-001",
            "guest_name": "Maria Santos",
            "guest_phone": "+55 21 98888-2222",
            "room_number": "103",
            "status": "PENDING",
            "total_amount": 760.0,  # 2 noites DOUBLE
        },
        
        # Hotel Montanha
        {
            "id": "res-montanha-001",
            "hotel_id": "hotel-montanha-002", 
            "guest_name": "Carlos Oliveira",
            "guest_phone": "+55 12 97777-1111",
            "room_number": "B1",
            "status": "CHECKED_IN",
            "total_amount": 1560.0,  # 3 noites SUITE
        },
        
        # Hotel Urbano
        {
            "id": "res-urbano-001",
            "hotel_id": "hotel-urbano-003",
            "guest_name": "Roberto Lima", 
            "guest_phone": "+55 11 96666-1111",
            "room_number": "601",
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


def seed_single_hotel() -> None:
    """Cria apenas um hotel (mantém compatibilidade com script original)."""
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
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--single":
        seed_single_hotel()
    else:
        seed_multi_tenant_data()
