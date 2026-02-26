# Passo 4: Hotel Context Implementation

**Objetivo**: Injetar políticas e informações do hotel no prompt da IA para que ela tenha contexto completo sobre as regras da propriedade.

**Status**: ✅ Completo e testado

---

## 📋 Visão Geral

Passo 4 envolve:

1. **Formalizar Hotel na camada de Domain** - Criar entidades, ValueObjects, e repositórios abstratos
2. **Persistir Hotel no banco de dados** - Criar tabela SQL e repository SQL
3. **Serviço de contexto** - Ler hotel do DB e formatar para IA
4. **Injetar no ConversationUseCase** - Adicionar contexto do hotel ao system prompt

### Resultado:

Quando um hóspede envia mensagem, a IA recebe DOIS contextos:

```
SISTEMA: "You are a helpful hotel assistant

CONTEXTO DO HOTEL:
- Nome: Hotel Automation
- Endereco: Avenida Central, 123, Brasilia - DF
- Check-in: 14:00
- Check-out: 12:00
- Politicas: Cancelamento gratis ate 24h antes | Nao aceitamos pets | Criancas ate 6 anos nao pagam
- Servicos: Wi-Fi, Piscina, Academia, Restaurante, Estacionamento
- Contato: +55 61 99999-0000

CONTEXTO DE RESERVA:
- Hospede: João Silva
- Status: confirmada
- Check-in: 2024-12-20
- Check-out: 2024-12-25
- Quarto: 302"

Hospede: "Qual é o horário de check-in?"

IA (com contexto): "Olá João! Check-in é às 14:00 hoje. 
Você pode usar Wi-Fi (senha disponível na recepção) 
e aproveitar nossa piscina e academia!"
```

---

## 🗂 Arquivos Criados/Modificados

### 1. Domain Layer

#### `app/domain/entities/hotel/hotel.py` (NEW)
```python
from app.domain.entities.hotel.policies import HotelPolicies

class Hotel:
    def __init__(
        self,
        hotel_id: str,
        name: str,
        address: str,
        contact_phone: str,
        policies: HotelPolicies,
        is_active: bool = True,
    ):
        self.hotel_id = hotel_id
        self.name = name
        self.address = address
        self.contact_phone = contact_phone
        self.policies = policies
        self.is_active = is_active
```

**Responsabilidade**: Agregado raiz representando um hotel com suas políticas.

#### `app/domain/entities/hotel/policies.py` (NEW)
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class HotelPolicies:
    checkin_time: str  # "14:00"
    checkout_time: str  # "12:00"
    cancellation_policy: str
    pet_policy: str
    child_policy: str
    amenities: str
```

**Responsabilidade**: ValueObject imutável encapsulando todas as políticas do hotel.

#### `app/domain/repositories/hotel_repository.py` (NEW)
```python
from abc import ABC, abstractmethod
from typing import Optional
from app.domain.entities.hotel.hotel import Hotel

class HotelRepository(ABC):
    @abstractmethod
    def get_active_hotel(self) -> Optional[Hotel]:
        pass
    
    @abstractmethod
    def save(self, hotel: Hotel) -> None:
        pass
```

**Responsabilidade**: Interface abstrata para persistência do hotel (DB-agnostic).

---

### 2. Infrastructure Layer

#### `app/infrastructure/persistence/sql/models.py` (MODIFIED)
Adicionada tabela HotelModel:

```python
class HotelModel(Base):
    __tablename__ = "hotels"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    checkin_time: Mapped[str] = mapped_column(String(5))  # "14:00"
    checkout_time: Mapped[str] = mapped_column(String(5))  # "12:00"
    cancellation_policy: Mapped[str] = mapped_column(Text)
    pet_policy: Mapped[str] = mapped_column(Text)
    child_policy: Mapped[str] = mapped_column(Text)
    amenities: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### `app/infrastructure/persistence/sql/hotel_repository_sql.py` (NEW)
```python
class HotelRepositorySQL(HotelRepository):
    def __init__(self, session):
        self.session = session
    
    def get_active_hotel(self) -> Optional[Hotel]:
        model = self.session.query(HotelModel).filter_by(is_active=True).first()
        if not model:
            return None
        
        policies = HotelPolicies(
            checkin_time=model.checkin_time,
            checkout_time=model.checkout_time,
            cancellation_policy=model.cancellation_policy,
            pet_policy=model.pet_policy,
            child_policy=model.child_policy,
            amenities=model.amenities,
        )
        
        return Hotel(
            hotel_id=str(model.id),
            name=model.name,
            address=model.address,
            contact_phone=model.contact_phone,
            policies=policies,
            is_active=model.is_active,
        )
    
    def save(self, hotel: Hotel) -> None:
        existing = self.session.query(HotelModel).get(hotel.hotel_id)
        
        if existing:
            # Update
            existing.name = hotel.name
            existing.address = hotel.address
            # ... atualizar outros campos
        else:
            # Insert
            model = HotelModel(
                id=hotel.hotel_id,
                name=hotel.name,
                # ... outros campos
            )
            self.session.add(model)
        
        self.session.commit()
```

**Responsabilidade**: Implementação SQL do HotelRepository. Converte entre models SQL e domínio.

---

### 3. Application Layer

#### `app/application/services/hotel_context_service.py` (REFACTORED)
```python
from app.domain.repositories.hotel_repository import HotelRepository

class HotelContextService:
    def __init__(self, hotel_repository: HotelRepository):
        self.hotel_repository = hotel_repository
    
    def get_context(self) -> str:
        """
        Recupera hotel ativo e formata contexto para IA.
        Retorna string vazia se nenhum hotel encontrado.
        """
        hotel = self.hotel_repository.get_active_hotel()
        
        if not hotel:
            return ""
        
        context = f"""CONTEXTO DO HOTEL:
- Nome: {hotel.name}
- Endereco: {hotel.address}
- Check-in: {hotel.policies.checkin_time}
- Check-out: {hotel.policies.checkout_time}
- Politicas: Cancelamento: {hotel.policies.cancellation_policy} | \
Pets: {hotel.policies.pet_policy} | Criancas: {hotel.policies.child_policy}
- Servicos: {hotel.policies.amenities}
- Contato: {hotel.contact_phone}"""
        
        return context
```

**Responsabilidade**: 
- Lê hotel do DB (via repository)
- Formata contexto legível para IA
- Retorna string para ser injetada no system prompt

#### `app/application/use_cases/conversation.py` (MODIFIED)
```python
class ConversationUseCase:
    def __init__(
        self,
        ai_service,
        context_service,  # ReservationContextService (Passo 3)
        hotel_context_service,  # NEW: HotelContextService (Passo 4)
    ):
        self.ai_service = ai_service
        self.context_service = context_service
        self.hotel_context_service = hotel_context_service
    
    async def execute(self, phone: str, message: str) -> str:
        # ... preparar histórico ...
        
        # NOVO: Montar system message com DUAL CONTEXT
        system_message = "You are a helpful hotel assistant"
        
        # Passo 4: Hotel context
        hotel_context = self.hotel_context_service.get_context()
        if hotel_context:
            system_message += f"\n\n{hotel_context}"
        
        # Passo 3: Reservation context
        reservation_context = self.context_service.get_context_for_phone(phone)
        if reservation_context:
            system_message += f"\n\n{reservation_context}"
        
        # Enviar para IA com contexto completo
        message_dicts.insert(0, {"role": "system", "content": system_message})
        
        response = self.ai_service.get_response(message_dicts)
        
        # ... salvar na cache e retornar ...
        return response
```

**Responsabilidade**:
- Recebe hotel_context_service injetado
- Chama HotelContextService.get_context() 
- Adiciona contexto do hotel ao system prompt
- Resultado: IA tem conhecimento completo

---

### 4. Dependency Injection

#### `app/interfaces/dependencies.py` (MODIFIED)
```python
def get_hotel_context_service() -> HotelContextService:
    """Criar e retornar HotelContextService configurado."""
    session = SessionLocal()
    hotel_repository = HotelRepositorySQL(session)
    return HotelContextService(hotel_repository)

def get_conversation_use_case(
    ai_service = Depends(get_ai_service),
    context_service = Depends(get_reservation_context_service),
) -> ConversationUseCase:
    """Injetar ambos os serviços de contexto."""
    hotel_context_service = get_hotel_context_service()  # NEW
    
    return ConversationUseCase(
        ai_service=ai_service,
        context_service=context_service,
        hotel_context_service=hotel_context_service,  # NEW
    )
```

**Responsabilidade**: Wiring de dependências. Assegura que HotelRepositorySQL é criado e injetado.

---

### 5. Database

#### `seed_hotel.py` (NEW)
```python
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.hotel_repository_sql import HotelRepositorySQL
from app.domain.entities.hotel.hotel import Hotel
from app.domain.entities.hotel.policies import HotelPolicies

session = SessionLocal()
repo = HotelRepositorySQL(session)

# Verificar se já existe hotel
existing_hotel = repo.get_active_hotel()
if existing_hotel:
    print("Hotel ativo ja existe, pulando seed.")
else:
    # Criar hotel de exemplo
    policies = HotelPolicies(
        checkin_time="14:00",
        checkout_time="12:00",
        cancellation_policy="Cancelamento gratis ate 24h antes do check-in",
        pet_policy="Nao aceitamos pets",
        child_policy="Criancas ate 6 anos nao pagam",
        amenities="Wi-Fi, Piscina, Academia, Restaurante, Estacionamento",
    )
    
    hotel = Hotel(
        hotel_id="h-001",
        name="Hotel Automation",
        address="Avenida Central, 123, Brasilia - DF",
        contact_phone="+55 61 99999-0000",
        policies=policies,
        is_active=True,
    )
    
    repo.save(hotel)
    print("Hotel criado com sucesso!")

session.close()
```

**Como usar**:
```bash
python seed_hotel.py
```

---

### 6. Database Migrations

#### `alembic/versions/5fa085db2e97_initial.py`
Migration criação inicial com tabela `hotels`:

```python
def upgrade() -> None:
    # ... criar outras tabelas ...
    
    op.create_table(
        'hotels',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('address', sa.String(500), nullable=False),
        sa.Column('contact_phone', sa.String(20), nullable=False),
        sa.Column('checkin_time', sa.String(5), nullable=True),
        sa.Column('checkout_time', sa.String(5), nullable=True),
        sa.Column('cancellation_policy', sa.Text(), nullable=True),
        sa.Column('pet_policy', sa.Text(), nullable=True),
        sa.Column('child_policy', sa.Text(), nullable=True),
        sa.Column('amenities', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
```

---

## 🧪 Testando Passo 4

### 1. Validar contexto do hotel:
```bash
python test_dual_context.py
```

Output esperado:
```
CONTEXTO DO HOTEL:
- Nome: Hotel Automation
- Endereco: Avenida Central, 123, Brasilia - DF
- Check-in: 14:00
- Check-out: 12:00
- Politicas: ...
- Servicos: Wi-Fi, Piscina, Academia, Restaurante, Estacionamento
- Contato: +55 61 99999-0000
```

### 2. Testar end-to-end:
```bash
# Iniciar servidor
python -m uvicorn app.main:app --reload

# Enviar mensagem WhatsApp via terminal (usando sandbox Twilio)
# Resposta da IA deve incluir informações do hotel
```

### 3. Verificar database:
```bash
psql hotel -c "SELECT name, contact_phone, is_active FROM hotels;"
```

---

## 🔄 Fluxo Completo: Passo 3 + Passo 4

```
1. Hóspede envia WhatsApp: "Qual é o horário de check-in?"

2. WhatsAppWebhook recebe e chama ConversationUseCase

3. ConversationUseCase executa:
   a) HotelContextService.get_context()
      → Query: SELECT * FROM hotels WHERE is_active=TRUE
      → Formato: "CONTEXTO DO HOTEL: ..."
   
   b) ReservationContextService.get_context_for_phone(phone)
      → Query: SELECT * FROM reservations WHERE phone=...
      → Formato: "CONTEXTO DE RESERVA: ..."
   
   c) Montar system prompt com AMBOS contextos
   
   d) Enviar para IA: {system_message, user_message, history}

4. IA processa com conhecimento completo:
   - Conhece políticas do hotel
   - Conhece dados específicos do hóspede
   - Responde de forma personalizada e contextual

5. Resposta retorna ao hóspede
```

---

## 📊 Benefícios

✅ **Contexto Completo para IA**: Sem hallucinations sobre políticas  
✅ **Personalizacao**: Respostas consideram dados do hóspede + hotel  
✅ **Escalavel**: Hotel info em DB, não hardcoded  
✅ **Manutenível**: Políticas editáveis via admin API (futuro)  
✅ **Clean Architecture**: Domain-agnostic, fácil de testar  

---

## 🚀 Próximos Passos

1. **Admin API** para editar hotel policies:
   ```python
   @app.put("/admin/hotel")
   async def update_hotel(hotel_update: HotelUpdateDTO):
       hotel_service.update(hotel_update)
       return {"status": "updated"}
   ```

2. **Multi-hotel support** (SaaS):
   - Adicionar `hotel_id` nas reservas
   - Passar hotel_id via WhatsApp webhook
   - HotelContextService busca hotel específico

3. **Cache hotel context**:
   - Redis cache de hotel_context com TTL
   - Reduz queries ao DB

4. **Testes automatizados**:
   - Unit tests para HotelContextService
   - Integration tests para ConversationUseCase
   - Mock tests para casos sem hotel

---

## 📝 Referências de Código

- **Domain Logic**: `app/domain/entities/hotel/`
- **Persistence**: `app/infrastructure/persistence/sql/hotel_repository_sql.py`
- **Service**: `app/application/services/hotel_context_service.py`
- **Integration**: `app/application/use_cases/conversation.py`
- **DI**: `app/interfaces/dependencies.py`
- **Seeding**: `seed_hotel.py`
- **Migrations**: `alembic/versions/5fa085db2e97_initial.py`
