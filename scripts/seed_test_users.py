"""Script para criar usuários de teste multi-tenant."""
import uuid
import os
import sys
from datetime import datetime
from passlib.hash import bcrypt

# Adicionar diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.persistence.sql.database import SessionLocal, init_db
from app.infrastructure.persistence.sql.models import UserModel


def create_test_users() -> None:
    """Cria usuários de teste para diferentes hotéis."""
    init_db()
    session = SessionLocal()

    print("👥 Criando usuários de teste multi-tenant...")

    # Usuários para teste de isolamento
    test_users = [
        # Hotel Paradise - Usuários com diferentes permissões
        {
            "id": "test-paradise-admin",
            "email": "admin.test@paradise.com",
            "password": "test123",
            "role": "admin",
            "hotel_id": "hotel-paradise-001",
            "name": "Admin Test Paradise",
            "description": "Administrador do Hotel Paradise para testes"
        },
        {
            "id": "test-paradise-user",
            "email": "user.test@paradise.com", 
            "password": "test123",
            "role": "user",
            "hotel_id": "hotel-paradise-001",
            "name": "User Test Paradise",
            "description": "Usuário comum do Hotel Paradise para testes"
        },
        
        # Hotel Montanha - Usuários para testar cross-hotel access
        {
            "id": "test-montanha-admin",
            "email": "admin.test@montanha.com",
            "password": "test123",
            "role": "admin",
            "hotel_id": "hotel-montanha-002",
            "name": "Admin Test Montanha",
            "description": "Administrador do Hotel Montanha para testes"
        },
        {
            "id": "test-montanha-user",
            "email": "user.test@montanha.com",
            "password": "test123", 
            "role": "user",
            "hotel_id": "hotel-montanha-002",
            "name": "User Test Montanha",
            "description": "Usuário comum do Hotel Montanha para testes"
        },
        
        # Hotel Urbano - Mais usuários para testes
        {
            "id": "test-urbano-manager",
            "email": "manager.test@urbano.com",
            "password": "test123",
            "role": "manager",
            "hotel_id": "hotel-urbano-003",
            "name": "Manager Test Urbano",
            "description": "Gerente do Hotel Urbano para testes"
        },
        {
            "id": "test-urbano-staff",
            "email": "staff.test@urbano.com",
            "password": "test123",
            "role": "staff",
            "hotel_id": "hotel-urbano-003", 
            "name": "Staff Test Urbano",
            "description": "Funcionário do Hotel Urbano para testes"
        },
        
        # Super Admin - Acesso a todos os hotéis
        {
            "id": "test-super-admin",
            "email": "superadmin.test@system.com",
            "password": "test123",
            "role": "admin",
            "hotel_id": None,  # Super admin sem hotel específico
            "name": "Super Admin Test",
            "description": "Super administrador para testes cross-hotel"
        },
        
        # Usuários sem hotel (devem ser bloqueados)
        {
            "id": "test-no-hotel-user",
            "email": "nohotel@test.com",
            "password": "test123",
            "role": "user",
            "hotel_id": None,  # Usuário sem hotel (deve ser bloqueado)
            "name": "No Hotel User",
            "description": "Usuário sem hotel para testar bloqueio"
        }
    ]
    
    created_count = 0
    for user_data in test_users:
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
            created_count += 1
            
            hotel_info = "Super Admin" if user_data["hotel_id"] is None else f"Hotel: {user_data['hotel_id']}"
            print(f"  ✅ Criado: {user_data['name']} ({user_data['role']}) - {hotel_info}")
            print(f"     📧 Email: {user_data['email']}")
            print(f"     🔑 Senha: {user_data['password']}")
            print(f"     📝 {user_data['description']}")
            print()
        else:
            print(f"  ⏭️  Já existe: {user_data['email']}")
    
    session.commit()
    session.close()
    
    print("=" * 60)
    print(f"🎉 {created_count} usuários de teste criados com sucesso!")
    print("=" * 60)
    print("\n🧪 Cenários de teste disponíveis:")
    print("\n1. Teste de isolamento básico:")
    print("   • Login: user.test@paradise.com / test123")
    print("   • Tente acessar dados do hotel-montanha-002 (deve ser bloqueado)")
    
    print("\n2. Teste de permissões admin:")
    print("   • Login: admin.test@paradise.com / test123")
    print("   • Deve acessar apenas dados do hotel-paradise-001")
    
    print("\n3. Teste cross-hotel (Super Admin):")
    print("   • Login: superadmin.test@system.com / test123")
    print("   • Deve acessar dados de TODOS os hotéis")
    
    print("\n4. Teste de bloqueio (usuário sem hotel):")
    print("   • Login: nohotel@test.com / test123")
    print("   • Deve ser bloqueado em qualquer operação")
    
    print("\n5. Teste de roles diferentes:")
    print("   • Manager: manager.test@urbano.com / test123")
    print("   • Staff: staff.test@urbano.com / test123")
    print("   • Verificar permissões específicas de cada role")


def create_performance_test_users() -> None:
    """Cria múltiplos usuários para testes de performance."""
    init_db()
    session = SessionLocal()

    print("⚡ Criando usuários para testes de performance...")
    
    # Criar 100 usuários distribuídos em 3 hotéis
    hotels = ["hotel-paradise-001", "hotel-montanha-002", "hotel-urbano-003"]
    roles = ["user", "staff", "manager"]
    
    created_count = 0
    for i in range(100):
        hotel_id = hotels[i % len(hotels)]
        role = roles[i % len(roles)]
        
        user_data = {
            "id": f"perf-user-{i:03d}",
            "email": f"user{i:03d}@test.com",
            "password": "perf123",
            "role": role,
            "hotel_id": hotel_id,
            "name": f"Performance User {i:03d}",
        }
        
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
            created_count += 1
    
    session.commit()
    session.close()
    
    print(f"⚡ {created_count} usuários de performance criados!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--performance":
        create_performance_test_users()
    else:
        create_test_users()
