# 🏗️ Arquitetura Completa - Hotel Automation

## 📋 Índice
1. [Overview Geral](#-overview-geral)
2. [Princípios Arquiteturais](#-princípios-arquiteturais)
3. [Camada Domain](#-camada-domain)
4. [Camada Application](#-camada-application)
5. [Camada Infrastructure](#-camada-infrastructure)
6. [Camada Interfaces](#-camada-interfaces)
7. [Fluxos Principais](#-fluxos-principais)
8. [Dependency Injection](#-dependency-injection-di)
9. [Tratamento de Erros](#-tratamento-de-erros)

---

## 🎯 Overview Geral

### Estrutura em Camadas

```
┌────────────────────────────────────────────────┐
│         INTERFACES (Controllers/API)            │  ← HTTP, Schemas, DI
├────────────────────────────────────────────────┤
│        APPLICATION (Use Cases/Services)        │  ← Orquestração
├────────────────────────────────────────────────┤
│      DOMAIN (Entities, Value Objects, Rules)   │  ← Lógica de Negócio
├────────────────────────────────────────────────┤
│  INFRASTRUCTURE (Persistence, Cache, APIs)     │  ← Implementação Real
└────────────────────────────────────────────────┘
```

### Diagrama de Dependências

```
Domain Layer (depende de nada)
    ↑
    │
Application Layer (depende de Domain)
    ↑
    │
Infrastructure & Interfaces (dependem de Application & Domain)
    ↑
    │
main.py (orquestra tudo)
```

---

## 🎓 Princípios Arquiteturais

### 1. Clean Architecture

**Objetivo:** Separar claramente responsabilidades e facilitar testes.

```
┌─────────────────────────────────────────┐
│   Regras de Negócio (Domain)            │ ← Nunca muda por motivos técnicos
│   - Entities                            │
│   - Value Objects                       │
│   - Domain Services                     │
└─────────────────────────────────────────┘
           ↑
           │ (usa)
┌─────────────────────────────────────────┐
│   Casos de Uso (Application)            │ ← Orquestra o domínio
│   - Use Cases                           │
│   - Application Services                │
│   - DTOs                                │
└─────────────────────────────────────────┘
           ↑
           │ (usa)
┌─────────────────────────────────────────┐
│   Camadas Externas (Infrastructure)     │ ← Pode mudar sem afetar negócio
│   - Database                            │
│   - Cache                               │
│   - APIs Externas                       │
└─────────────────────────────────────────┘
```

**Benefícios:**
- ✅ Domain fica testável sem dependências externas
- ✅ Fácil trocar PostgreSQL por MongoDB (implementar nova Repository)
- ✅ Centraliza lógica de negócio em um lugar

### 2. Domain-Driven Design (DDD)

**Conceitos:**
- **Aggregate Root:** Entidade que agrupa objetos relacionados (ex: `Reservation`)
- **Value Object:** Objeto imutável sem identidade (ex: `Message`, `PhoneNumber`)
- **Bounded Context:** Límites lógicos do domínio
- **Repository:** Interface para persistência

**Aplicação no projeto:**
```
┌──────────────────────────────┐
│   Bounded Context: Hotel     │
├──────────────────────────────┤
│ ┌────────────────────────┐   │
│ │ Aggregate: Reservation │   │ ← Root Entity
│ │                        │   │
│ │ - id                   │   │
│ │ - guest_name           │   │
│ │ - guest_phone (VO)     │   │
│ │ - status               │   │
│ │ - messages (VO[])      │   │ ← Coleção de Value Objects
│ │                        │   │
│ │ Métodos:               │   │
│ │ + check_in()           │   │
│ │ + check_out()          │   │
│ │ + cancel()             │   │
│ └────────────────────────┘   │
└──────────────────────────────┘
```

### 3. SOLID Principles

| Princípio | Aplicação | Exemplo |
|-----------|-----------|---------|
| **S**ingle Responsibility | Uma classe, uma razão para mudar | `ReservationRepositorySQL` apenas quer falar com banco |
| **O**pen/Closed | Aberto para extensão, fechado para mudança | `ReservationRepository` (interface) permite novas implementações |
| **L**iskov Substitution | Subclasses substituem a interface | `ReservationRepositorySQL` ↔ `ReservationRepositoryMemory` |
| **I**nterface Segregation | Interfaces específicas | `CacheRepository`, `AIService`, `ReservationRepository` |
| **D**ependency Inversion | Depender de abstrações | Use Case recebe `ReservationRepository` (abstração) |

---

## 🌱 Camada Domain

### Responsabilidades
- ✅ Lógica de negócio pura (sem dependências externas)
- ✅ Garantir invariantes (regras que nunca podem ser quebradas)
- ✅ Definir interfaces (Repositories)
- ✅ Lançar exceções de domínio

### Estrutura de Diretórios

```
app/domain/
├── entities/                    ← Aggregate Roots
│   ├── reservation/
│   │   ├── reservation.py       ← Aggregate Root (4 arquivos nessa pasta)
│   │   ├── reservation_status.py
│   │   └── stay_period.py
│   ├── customer/
│   │   ├── customer.py
│   │   └── customer_status.py
│   ├── hotel/
│   │   ├── hotel.py
│   │   └── policies.py
│   └── payment/
│       ├── payment.py
│       └── payment_status.py
├── value_objects/               ← Immutable objects
│   ├── message.py
│   ├── phone_number.py
│   └── __init__.py
├── repositories/                ← Interfaces (abstrações)
│   ├── reservation_repository.py
│   ├── cache_repository.py
│   └── conversation_cache_repository.py
├── services/                    ← Domain services (se necessário)
│   └── __init__.py
├── exceptions.py                ← Domain exceptions
└── __init__.py
```

### 1. Aggregate Root: Reservation

**O que é Aggregate Root?**
Uma entidade que é o "portão de entrada" para agregar relacionadas. No nosso caso, `Reservation` é o AR porque agrupa:
- Hóspede (guest_name, guest_phone)
- Status
- Período de estadia

```python
class Reservation:
    """
    Aggregate Root para reservas de hotel.
    
    Invariantes (regras que SEMPRE devem ser verdadeiras):
    1. id nunca é None
    2. guest_phone é um PhoneNumber válido
    3. status é um ReservationStatus válido
    4. Transições de status seguem as regras de negócio
    """
    
    def __init__(self, id, guest_name, guest_phone: PhoneNumber, status: ReservationStatus):
        self.id = id                                    # Identidade única
        self.guest_name = guest_name                    # Atributo
        self.guest_phone = guest_phone                  # Value Object
        self.status = status                            # Enum (Value Object)
    
    def check_in(self):
        """Muda status para CHECKED_IN se possível."""
        if self.status != ReservationStatus.CONFIRMED:
            raise InvalidCheckInState(...)
        self.status = ReservationStatus.CHECKED_IN
    
    def to_dict(self):
        """Serializa para persistência."""
        return {...}
```

**Diagrama UML: Reservation Aggregate**

```
┌─────────────────────────────────┐
│      Reservation (AR)           │ ← Aggregate Root
│─────────────────────────────────│
│ - id: str                       │
│ - guest_name: str               │
│ - guest_phone: PhoneNumber (VO) │ ← Value Object
│ - status: ReservationStatus (VO)│ ← Enum (também VO)
│ - messages: List[Message] (VO)  │ ← Collection de VOs
│─────────────────────────────────│
│ + check_in()                    │
│ + check_out()                   │
│ + cancel()                      │
│ + to_dict()                     │
└─────────────────────────────────┘
```

### 2. Value Objects

**O que é Value Object?**
Um objeto que:
- NÃO tem identidade (dois `Message` é o mesmo se tiverem role="user" e content="oi")
- É IMUTÁVEL após criação
- Encapsula validação
- Pode ser copiad/descartado

#### Message (Value Object)

```python
class Message:
    """
    Value Object que representa uma mensagem em uma conversa.
    
    Invariantes:
    - role ∈ {"user", "assistant", "system"}
    - content nunca é empty ou whitespace
    """
    
    VALID_ROLES = {"user", "assistant", "system"}
    
    def __init__(self, role: str, content: str):
        # Validação (invariantes no construtor)
        if role not in self.VALID_ROLES:
            raise ValueError(f"Invalid role '{role}'")
        
        if not content or not content.strip():
            raise ValueError("Message content cannot be empty")
        
        # Imutável: usando _propriedade
        self._role = role
        self._content = content.strip()
    
    # Sem setters! Imutável.
    @property
    def role(self) -> str:
        return self._role
    
    @property
    def content(self) -> str:
        return self._content
    
    def to_dict(self):
        """Serializa para persistência."""
        return {"role": self._role, "content": self._content}
    
    def is_user_message(self) -> bool:
        return self._role == "user"
```

**Características:**
- ✅ Sem `id` (não tem identidade)
- ✅ Imutável (não há `.set_content()`)
- ✅ Encapsula validação (role e content)
- ✅ Value Object! Pode descartar sem perder identidade

#### PhoneNumber (Value Object)

```python
class PhoneNumber:
    """
    Value Object que encapsula um número de telefone.
    
    Invariante: Formato válido de telefone
    """
    
    def __init__(self, phone: str):
        if not self._is_valid(phone):
            raise InvalidPhoneNumber(f"Invalid phone: {phone}")
        self.value = phone
    
    def _is_valid(self, phone: str) -> bool:
        # Lógica de validação...
        return len(phone) >= 10
    
    def __str__(self):
        return self.value
    
    def __eq__(self, other):
        return self.value == other.value if isinstance(other, PhoneNumber) else False
```

### 3. Repositories (Interfaces)

**O que é Repository?**
Uma interface que define como o Domain quer persistir/recuperar dados, SEM saber COMO isso é feito.

```python
from abc import ABC, abstractmethod

class ReservationRepository(ABC):
    """
    Interface que o Domain define.
    
    Diz O QUE, não COMO.
    """
    
    @abstractmethod
    def save(self, reservation: Reservation) -> None:
        """Persiste uma reserva (nova ou atualiza existente)."""
        pass
    
    @abstractmethod
    def find_by_phone_number(self, phone_number: str) -> Optional[Reservation]:
        """Recupera uma reserva pelo número do hóspede."""
        pass
```

**Vantagem:**
- Domain não sabe se é PostgreSQL, MongoDB ou CSV
- Use Case recebe a interface, não a implementação
- Fácil testar: passar um `ReservationRepositoryMemory`

```
Domain (Define)
    ↑
    │ implements
┌───┴──────────────────────────────┐
│ ReservationRepositorySQL         │
│ ReservationRepositoryMemory      │ ← Infra implementa
│ ReservationRepositoryMongo (novo)│
└──────────────────────────────────┘
```

### 4. Enums (Value Objects)

```python
from enum import Enum

class ReservationStatus(Enum):
    """Value Object representando estados válidos de uma reserva."""
    
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"
    CANCELLED = "CANCELLED"
```

### 5. Domain Exceptions

```python
class DomainException(Exception):
    """Base para exceções de domínio."""
    pass

class InvalidCheckInState(DomainException):
    """Lançada quando tentam fazer check-in em estado inválido."""
    pass

class InvalidReservationStatus(DomainException):
    """Lançada quando transição de status é inválida."""
    pass

class InvalidPhoneNumber(DomainException):
    """Lançada quando PhoneNumber é inválido."""
    pass
```

**Diagrama: Entities & Value Objects**

```
┌──────────────────────────────────────────────────────┐
│                  Domain Layer                        │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌───────────────────────────────────────────┐      │
│  │  Reservation (Entity/Aggregate Root)      │      │
│  │  ├─ id (identity)                         │      │
│  │  ├─ guest_name                            │      │
│  │  ├─ guest_phone: PhoneNumber (VO) ──┐     │      │
│  │  ├─ status: ReservationStatus (VO) ─┼─┐   │      │
│  │  └─ messages: List[Message] (VO)    │ │   │      │
│  └───────────────────────────────────────────┘      │
│                                        │ │           │
│  ┌──────────────────┐  ┌────────────────┼──┐        │
│  │ PhoneNumber (VO) │  │ ReservationStatus  │       │
│  │ ───────────────  │  │ ────────────────── │       │
│  │ - value: str     │  │ - PENDING          │       │
│  │ - is_valid()     │  │ - CONFIRMED        │       │
│  │ - __eq__()       │  │ - CHECKED_IN       │       │
│  │ - __str__()      │  │ - CHECKED_OUT      │       │
│  │ (IMUTÁVEL)       │  │ - CANCELLED        │       │
│  └──────────────────┘  └────────────────────┘       │
│                                                      │
│  ┌──────────────────┐                               │
│  │ Message (VO)     │                               │
│  │ ──────────────── │                               │
│  │ - role: str      │                               │
│  │ - content: str   │                               │
│  │ - to_dict()      │                               │
│  │ - is_user_msg()  │                               │
│  │ (IMUTÁVEL)       │                               │
│  └──────────────────┘                               │
│                                                      │
│  ┌───────────────────────────────────────────┐      │
│  │  Interfaces (Contracts)                   │      │
│  │  ├─ ReservationRepository                 │      │
│  │  │  + save()                              │      │
│  │  │  + find_by_phone_number()              │      │
│  │  ├─ CacheRepository                       │      │
│  │  │  + get()                               │      │
│  │  │  + set()                               │      │
│  │  │  + delete()                            │      │
│  │  ├─ AIService                             │      │
│  │  │  + chat()                              │      │
│  │  │  + complete()                          │      │
│  │  └─ ConversationCacheRepository           │      │
│  └───────────────────────────────────────────┘      │
│                                                      │
│  ┌───────────────────────────────────────────┐      │
│  │  Exceptions                               │      │
│  │  ├─ DomainException                       │      │
│  │  ├─ InvalidCheckInState                   │      │
│  │  ├─ InvalidReservationStatus              │      │
│  │  └─ InvalidPhoneNumber                    │      │
│  └───────────────────────────────────────────┘      │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## 🚀 Camada Application

### Responsabilidades
- ✅ Orquestra o Domain (coordena Entities, Value Objects, Repositories)
- ✅ Implementa casos de uso (Use Cases)
- ✅ Traduz exceções Domain → Application
- ✅ Define DTOs (objetos de transferência de dados)

### Estrutura de Diretórios

```
app/application/
├── use_cases/                                      ← Casos de uso
│   ├── checkin_via_whatsapp.py
│   └── conversation.py
├── services/                                      ← Serviços
│   ├── ai_service.py
│   └── __init__.py
├── dto/                                           ← Data Transfer Objects
│   ├── checkin_request_dto.py
│   ├── checkin_response_dto.py
│   └── __init__.py
├── exceptions.py                                  ← Exceções Application
└── __init__.py
```

### 1. Use Cases

**O que é um Use Case?**
Uma classe que orquestra um fluxo de negócio específico:
1. Recebe entrada
2. Usa Domain Entities, Value Objects, Repositories
3. Executa lógica de negócio
4. Retorna resultado

#### CheckInViaWhatsAppUseCase

```python
class CheckInViaWhatsAppUseCase:
    """
    Caso de uso para fazer check-in via WhatsApp.
    
    Fluxo:
    1. Recebe o número de telefone
    2. Tenta recuperar da cache
    3. Se não found, busca no repo
    4. Valida a reserva
    5. Executa check_in()
    6. Salva na cache
    """
    
    def __init__(
        self,
        reservation_repository: ReservationRepository,  # ← Abstração (interface)
        cache_repository: CacheRepository,               # ← Abstração (interface)
    ):
        """Injeta as interfaces, não as implementações."""
        self.reservation_repo = reservation_repository
        self.cache_repo = cache_repository
    
    def execute(self, request_dto: CheckinRequestDTO) -> CheckinResponseDTO:
        """
        Executa o fluxo de check-in.
        
        Args:
            request_dto: DTO com dados da requisição
        
        Returns:
            CheckinResponseDTO com resultado
        """
        # 1. Tenta cache primeiro (rápido)
        cached = self.cache_repo.get(request_dto.phone_number)
        if cached:
            return CheckinResponseDTO(message="✅ Check-in sucesso (cache)!")
        
        # 2. Se não tiver cache, busca no repo (banco de dados)
        reservation = self.reservation_repo.find_by_phone_number(
            request_dto.phone_number
        )
        
        if not reservation:
            return CheckinResponseDTO(message="❌ Nenhuma reserva encontrada")
        
        # 3. Executa lógica de domínio
        reservation.check_in()  # ← Domain logic (pode lançar exceção)
        
        # 4. Persiste mudanças
        self.reservation_repo.save(reservation)
        
        # 5. Atualiza cache
        self.cache_repo.set(request_dto.phone_number, reservation.to_dict())
        
        return CheckinResponseDTO(message="✅ Check-in feito com sucesso!")
```

#### ConversationUseCase

```python
class ConversationUseCase:
    """
    Caso de uso para conversas multi-turn com IA.
    
    Fluxo:
    1. Recupera histórico do cache
    2. Adiciona mensagem do usuário
    3. Chama IA
    4. Adiciona resposta da IA
    5. Atualiza cache
    6. Loga interação
    7. Envia mensagem (se messaging disponível)
    """
    
    def __init__(
        self,
        ai_service: AIService,                          # ← Interface
        reservation_repo: ReservationRepository,         # ← Interface
        cache_repository: CacheRepository,               # ← Interface
        messaging: Optional[object] = None,              # ← Opcional
        logger: Optional[ConversationLogger] = None,     # ← Opcional
    ):
        self.ai = ai_service
        self.reservation_repo = reservation_repo
        self.cache_repository = cache_repository
        self.messaging = messaging
        self.logger = logger or ConversationLogger()
    
    def execute(self, phone: str, text: str) -> str:
        """
        Executa uma rodada de conversa.
        
        Fluxo:
        1. Pega histórico (List[dict])
        2. Converte para Message VOs
        3. Adiciona nova mensagem
        4. Chama IA
        5. Adiciona resposta
        6. Persiste histórico
        7. Loga
        """
        try:
            # 1. Get history
            history_dicts = self._get_conversation_history(phone)
            
            # 2. Convert to Message VOs
            messages: List[Message] = [
                Message(role=msg["role"], content=msg["content"])
                for msg in history_dicts
            ]
            
            # 3. Add user message
            user_msg = Message(role="user", content=text)
            messages.append(user_msg)
            
            # 4. Call AI
            ai_response = self._call_ai(messages)
            
            # 5. Add assistant message
            assistant_msg = Message(role="assistant", content=ai_response)
            messages.append(assistant_msg)
            
            # 6. Update cache
            self._update_conversation_history(phone, messages)
            
            # 7. Log interaction
            self._log_interaction(phone, text, ai_response)
            
            # 8. Send via messaging (optional)
            if self.messaging:
                self._send_message(phone, ai_response)
            
            return ai_response
            
        except (CacheError, AIServiceError) as e:
            raise ConversationFailed(f"Conversation failed: {str(e)}")
```

### 2. DTOs (Data Transfer Objects)

**O que é DTO?**
Um objeto que:
- Carrega dados entre camadas
- NÃO contém lógica de negócio
- Apenas encapsula estrutura de dados
- Valida tipos (Pydantic)

```python
# checkin_request_dto.py
class CheckinRequestDTO:
    """
    DTO para requisição de check-in.
    
    Apenas carrega dados, sem lógica.
    """
    def __init__(self, phone_number: str):
        self.phone_number = phone_number

# checkin_response_dto.py
class CheckinResponseDTO:
    """
    DTO para resposta de check-in.
    
    Carries result back to caller.
    """
    def __init__(self, message: str):
        self.message = message
```

**DTO vs Entity:**
| Aspecto | DTO | Entity |
|--------|-----|--------|
| Responsabilidade | Transferir dados | Encapsular lógica |
| Lógica | Nenhuma | Sim (invariantes) |
| Identity | Não | Sim (id) |
| Mutabilidade | Mutável | Pode ser mutável ou imutável |
| Exemplo | `CheckinRequestDTO` | `Reservation` |

### 3. Application Services

```python
# ai_service.py (abstração)
from abc import ABC, abstractmethod

class AIService(ABC):
    """
    Interface que define contrato com serviços IA.
    
    O Domain/Application não sabe se é OpenAI, Anthropic, ou local.
    """
    
    @abstractmethod
    def chat(self, messages: List[dict]) -> str:
        """
        Sends messages and gets response.
        
        Args:
            messages: [{"role": "user", "content": "..."}]
        
        Returns:
            AI response text
        """
        pass
    
    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Complete a prompt."""
        pass
```

### 4. Application Exceptions

```python
class ApplicationException(Exception):
    """Base para exceções de Application."""
    pass

class CheckInFailed(ApplicationException):
    """Lançada quando check-in falha."""
    pass

class ConversationFailed(ApplicationException):
    """Lançada quando conversa falha."""
    pass

class AIServiceError(ApplicationException):
    """Lançada quando IA falha."""
    pass

class CacheError(ApplicationException):
    """Lançada quando cache falha."""
    pass
```

**Diagrama: Application Layer**

```
┌────────────────────────────────────────────────────┐
│          Application Layer                         │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────────────────────────────────────┐     │
│  │  Use Cases (Orquestração)                │     │
│  │  ├─ CheckInViaWhatsAppUseCase            │     │
│  │  │  ├─ execute(request) → response       │     │
│  │  │  └─ (usa: Repo, Cache, Domain logic)  │     │
│  │  └─ ConversationUseCase                  │     │
│  │     ├─ execute(phone, text) → response   │     │
│  │     └─ (usa: AI, Repo, Cache, Logger)    │     │
│  └──────────────────────────────────────────┘     │
│                                                    │
│  ┌──────────────────────────────────────────┐     │
│  │  Services (Interfaces)                   │     │
│  │  ├─ AIService                            │     │
│  │  │  + chat()                             │     │
│  │  │  + complete()                         │     │
│  │  └─ (implementação: Infrastructure)      │     │
│  └──────────────────────────────────────────┘     │
│                                                    │
│  ┌──────────────────────────────────────────┐     │
│  │  DTOs (Transferência de dados)           │     │
│  │  ├─ CheckinRequestDTO                    │     │
│  │  ├─ CheckinResponseDTO                   │     │
│  │  └─ (sem lógica, apenas dados)           │     │
│  └──────────────────────────────────────────┘     │
│                                                    │
│  ┌──────────────────────────────────────────┐     │
│  │  Exceptions                              │     │
│  │  ├─ ApplicationException                 │     │
│  │  ├─ CheckInFailed                        │     │
│  │  ├─ ConversationFailed                   │     │
│  │  ├─ AIServiceError                       │     │
│  │  └─ CacheError                           │     │
│  └──────────────────────────────────────────┘     │
│                                                    │
└────────────────────────────────────────────────────┘
         ↓ (depende)
    Domain Layer
```

---

## 🔧 Camada Infrastructure

### Responsabilidades
- ✅ Implementa Repositories (persiste em DB)
- ✅ Implementa Cache (Redis, Memcached)
- ✅ Implementa serviços externos (OpenAI, WhatsApp, etc)
- ✅ Configura banco de dados
- ✅ Logging persistente

### Estrutura de Diretórios

```
app/infrastructure/
├── persistence/                                    ← Repositories implementados
│   ├── sql/
│   │   ├── database.py          ← SessionLocal, init_db()
│   │   ├── models.py            ← SQLAlchemy models
│   │   └── reservation_repository_sql.py
│   └── memory/
│       └── reservation_repository_memory.py
├── cache/                                         ← Cache implementations
│   └── redis_repository.py
├── ai/                                            ← AI integrations
│   ├── __init__.py
│   └── openai_client.py
├── logging/                                       ← Business logic logging
│   ├── __init__.py
│   └── conversation_logger.py
├── messaging/                                     ← Messaging implementations
│   └── __init__.py
├── payment/                                       ← Payment integrations
│   └── __init__.py
└── __init__.py
```

### 1. Persistence: Repositories Implementados

#### ReservationRepositorySQL

```python
from app.domain.repositories.reservation_repository import ReservationRepository
from app.domain.entities.reservation.reservation import Reservation

class ReservationRepositorySQL(ReservationRepository):
    """
    Implementação SQL do Repository.
    
    Recebe a interface (ReservationRepository) e implementa
    com SQL (PostgreSQL).
    """
    
    def __init__(self, session):
        """Session é a conexão com database."""
        self.session = session
    
    def find_by_phone_number(self, phone_number: str) -> Optional[Reservation]:
        """
        Query SQL e retorna Domain Entity.
        
        SQL:
            SELECT * FROM reservations WHERE guest_phone = ?
        """
        model = self.session.query(ReservationModel).filter_by(
            guest_phone=phone_number
        ).first()
        
        if model:
            # Converte SQLAlchemy model → Domain Entity
            return Reservation(
                reservation_id=str(model.id),
                guest_name=model.guest_name,
                guest_phone=PhoneNumber(model.guest_phone),
                status=ReservationStatus[model.status],
            )
        return None
    
    def save(self, reservation: Reservation) -> None:
        """
        Persiste a entidade de domínio.
        
        SQL:
            INSERT INTO reservations (...) VALUES (...)
            OR
            UPDATE reservations SET ... WHERE id = ...
        """
        existing = self.session.query(ReservationModel).filter_by(
            guest_phone=str(reservation.guest_phone)
        ).first()
        
        if existing:
            # Update
            existing.status = reservation.status.name
            existing.guest_name = reservation.guest_name
        else:
            # Insert
            model = ReservationModel(
                guest_name=reservation.guest_name,
                guest_phone=str(reservation.guest_phone),
                status=reservation.status.name,
            )
            self.session.add(model)
        
        self.session.commit()
```

#### ReservationRepositoryMemory

```python
class ReservationRepositoryMemory(ReservationRepository):
    """
    Implementação em memória (para testes).
    
    Implementa MESMA interface mas sem DB real.
    """
    
    def __init__(self):
        self._store = {}
    
    def find_by_phone_number(self, phone_number: str) -> Optional[Reservation]:
        return self._store.get(phone_number)
    
    def save(self, reservation: Reservation) -> None:
        self._store[str(reservation.guest_phone)] = reservation
```

**Padrão Strategy:** Mesma interface, múltiplas implementações!

```
ReservationRepository (Interface)
    ↑ implements
    ├── ReservationRepositorySQL ← Production (PostgreSQL)
    ├── ReservationRepositoryMemory ← Testing (em memória)
    └── ReservationRepositoryMongo ← Future (MongoDB)
```

### 2. Cache: Redis Implementation

```python
from app.domain.repositories.cache_repository import CacheRepository
import redis

class RedisRepository(CacheRepository):
    """
    Implementação Redis do Cache.
    
    Persiste dados em cache remoto.
    """
    
    def __init__(self):
        """Conecta ao Redis (credenciais do .env)."""
        self.client = redis.Redis(
            host=os.getenv("REDIS_HOST"),
            port=int(os.getenv("REDIS_PORT")),
            username=os.getenv("REDIS_USERNAME"),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True,
        )
    
    def get(self, key: str):
        """Recupera do Redis."""
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    def set(self, key: str, value, ttl_seconds: int = 3600):
        """
        Salva no Redis com TTL.
        
        Redis:
            SET key value EX 3600  (expira em 3600 segundos)
        """
        self.client.set(key, json.dumps(value), ex=ttl_seconds)
    
    def delete(self, key: str):
        """Remove do Redis."""
        self.client.delete(key)
    
    def exists(self, key: str) -> bool:
        """Checa se existe."""
        return self.client.exists(key) > 0
    
    def clear(self):
        """Limpa tudo (cuidado em produção!)."""
        self.client.flushdb()
```

### 3. AI: OpenAI Client

```python
from app.application.services.ai_service import AIService
import openai

class OpenAIClient(AIService):
    """
    Implementação OpenAI do serviço de IA.
    
    Implementa interface AIService usando OpenAI SDK v2.x
    """
    
    def __init__(self):
        """Inicializa cliente OpenAI."""
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.client = openai.OpenAI()
    
    def chat(self, messages: List[dict]) -> str:
        """
        Chama OpenAI Chat API.
        
        Args:
            messages: [
                {"role": "system", "content": "Você é um assistente"},
                {"role": "user", "content": "Olá!"}
            ]
        
        Returns:
            Resposta da IA
        """
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
        )
        
        return response.choices[0].message.content
    
    def complete(self, prompt: str) -> str:
        """Completação simples."""
        response = self.client.completions.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=100,
        )
        return response.choices[0].text
```

### 4. Database: SQLAlchemy Setup

```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Cria todas as tabelas."""
    from .models import Base
    Base.metadata.create_all(bind=engine)

# models.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ReservationModel(Base):
    """SQLAlchemy model (representação no banco)."""
    __tablename__ = "reservations"
    
    id = Column(Integer, primary_key=True)
    guest_name = Column(String)
    guest_phone = Column(String, unique=True)
    status = Column(String)
```

### 5. Logging: ConversationLogger

```python
class ConversationLogger:
    """
    Logger persistente para conversas.
    
    Salva todas as interações em JSON para auditoria.
    """
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / "conversation_history.json"
    
    def log_interaction(
        self,
        phone: str,
        user_message: str,
        ai_response: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        model: str = "gpt-3.5-turbo",
        metadata: Optional[Dict] = None,
    ) -> None:
        """
        Registra uma interação.
        
        Estrutura no JSON:
        {
            "timestamp": "2026-02-21T11:06:45",
            "phone": "556199999999",
            "user_message": "Olá",
            "ai_response": "Oi! Como posso ajudar?",
            "tokens": {"input": 1, "output": 8, "total": 9},
            "cost": {"input_usd": 0.0, "output_usd": 0.000012, "total_usd": 0.000012},
            "metadata": {"source": "conversation_use_case"}
        }
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "phone": phone,
            "user_message": user_message[:500],
            "ai_response": ai_response[:500],
            "tokens": {
                "input": tokens_input,
                "output": tokens_output,
                "total": tokens_input + tokens_output,
            },
            "cost": {
                "input_usd": (tokens_input / 1_000_000) * 0.50,
                "output_usd": (tokens_output / 1_000_000) * 1.50,
                "total_usd": ((tokens_input / 1_000_000) * 0.50) + ((tokens_output / 1_000_000) * 1.50),
            },
            "metadata": metadata or {},
        }
        
        # Carrega histórico e adiciona entrada
        conversations = self._load_or_create()
        conversations.append(entry)
        
        # Persiste
        with open(self.log_file, 'w') as f:
            json.dump(conversations, f, indent=2)
```

**Diagrama: Infrastructure Layer**

```
┌────────────────────────────────────────────────────┐
│         Infrastructure Layer                       │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────────────────────────────────────┐     │
│  │  Persistence (Implementations)           │     │
│  │  ├─ ReservationRepositorySQL             │     │
│  │  │  └─ implements ReservationRepository  │     │
│  │  ├─ ReservationRepositoryMemory          │     │
│  │  │  └─ implements ReservationRepository  │     │
│  │  └─ Database setup (SessionLocal)        │     │
│  └──────────────────────────────────────────┘     │
│                              ↓                     │
│                      PostgreSQL / SQLite           │
│                                                    │
│  ┌──────────────────────────────────────────┐     │
│  │  Cache (Implementations)                 │     │
│  │  ├─ RedisRepository                      │     │
│  │  │  └─ implements CacheRepository        │     │
│  │  └─ Connection pool to Redis Cloud       │     │
│  └──────────────────────────────────────────┘     │
│                              ↓                     │
│                      Redis Cloud                   │
│                                                    │
│  ┌──────────────────────────────────────────┐     │
│  │  AI Services (Implementations)           │     │
│  │  ├─ OpenAIClient                         │     │
│  │  │  └─ implements AIService              │     │
│  │  └─ API calls to OpenAI                  │     │
│  └──────────────────────────────────────────┘     │
│                              ↓                     │
│                      OpenAI API                    │
│                                                    │
│  ┌──────────────────────────────────────────┐     │
│  │  Logging (Implementations)               │     │
│  │  └─ ConversationLogger                   │     │
│  │     └─ writes to logs/conversation.json  │     │
│  └──────────────────────────────────────────┘     │
│                              ↓                     │
│                      JSON Files                    │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

## 🎨 Camada Interfaces

### Responsabilidades
- ✅ HTTP endpoints (FastAPI)
- ✅ Validação de input (Pydantic Schemas)
- ✅ Transformação Schema ↔ DTO
- ✅ Tratamento de HTTP erros
- ✅ Dependency Injection

### Estrutura de Diretórios

```
app/interfaces/
├── api/                                           ← Endpoints HTTP
│   ├── __init__.py
│   └── whatsapp_webhook.py
├── schemas.py                                     ← Pydantic models (HTTP)
├── converters.py                                  ← Schema ↔ DTO
├── exceptions.py                                  ← HTTP exceptions
├── dependencies.py                                ← DI container
└── __init__.py
```

### 1. Schemas (Pydantic Models)

**O que é Schema?**
Um modelo Pydantic que:
- Valida dados HTTP (JSON input/output)
- É específico para HTTP (não é DTO!)
- Valida tipos automaticamente
- Gera documentação Swagger

```python
from pydantic import BaseModel, Field

class CheckInRequest(BaseModel):
    """Schema para requisição HTTP de check-in."""
    phone_number: str = Field(..., description="Número de telefone do hóspede")
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone_number": "5561999999999"
            }
        }

class CheckInResponse(BaseModel):
    """Schema para resposta HTTP de check-in."""
    message: str = Field(..., description="Mensagem de resultado")
    success: bool = Field(..., description="Sucesso ou não")

class ConversationRequest(BaseModel):
    """Schema para requisição HTTP de conversa."""
    phone: str = Field(..., description="Número de telefone")
    text: str = Field(..., description="Mensagem do usuário")

class ConversationResponse(BaseModel):
    """Schema para resposta HTTP de conversa."""
    response: str = Field(..., description="Resposta da IA")
    timestamp: str = Field(..., description="Quando foi respondido")
```

### 2. Converters (Schema ↔ DTO)

**O que é Converter?**
Traduz entre camadas:
- FastAPI recebe via `Schema` (HTTP layer)
- Converter transforma em `DTO` (Application layer)
- Use Case processa
- DTO volta em `Schema` (HTTP response)

```python
class RequestConverters:
    """Converte HTTP Schema → Application DTO."""
    
    @staticmethod
    def checkin_request_schema_to_dto(schema: CheckInRequest) -> CheckinRequestDTO:
        """Schema → DTO."""
        return CheckinRequestDTO(phone_number=schema.phone_number)

class ResponseConverters:
    """Converte Application DTO → HTTP Schema."""
    
    @staticmethod
    def checkin_response_dto_to_schema(dto: CheckinResponseDTO) -> CheckInResponse:
        """DTO → Schema."""
        return CheckInResponse(
            message=dto.message,
            success="sucesso" in dto.message.lower()
        )
```

**Fluxo com Converter:**

```
HTTP POST /checkin
    ↓
FastAPI recebe JSON
    ↓
Pydantic valida → CheckInRequest (Schema)
    ↓
Converter.to_dto()
    ↓
CheckinRequestDTO (DTO)
    ↓
Use Case.execute(dto)
    ↓
CheckinResponseDTO (DTO)
    ↓
Converter.to_schema()
    ↓
CheckInResponse (Schema)
    ↓
FastAPI serializa → JSON
    ↓
HTTP 200 OK + JSON
```

### 3. API Endpoints (FastAPI)

```python
from fastapi import APIRouter, Depends

router = APIRouter()

@router.post("/webhook/whatsapp")
def whatsapp_webhook(
    payload: WhatsAppMessage,  # ← FastAPI valida Schema automaticamente
    use_case: CheckInViaWhatsAppUseCase = Depends(get_checkin_use_case),
) -> dict:
    """
    Endpoint WhatsApp webhook.
    
    FastAPI automaticamente:
    1. Valida JSON com WhatsAppMessage schema
    2. Injeta use_case via get_checkin_use_case()
    3. Converte resposta para JSON
    """
    
    # SimpleParse mensagem
    if "checkin" in payload.message.lower():
        # Converte Schema → DTO
        request_dto = CheckinRequestDTO(phone_number=payload.phone)
        
        # Executa
        response_dto = use_case.execute(request_dto)
        
        # Converte DTO → Schema
        response_schema = CheckInResponse(
            message=response_dto.message,
            success=True
        )
        
        return response_schema.model_dump()
    
    return {"reply": "Mensagem recebida."}

@router.post("/api/conversation")
def conversation_endpoint(
    request: ConversationRequest,  # ← Schema
    use_case: ConversationUseCase = Depends(get_conversation_use_case),
) -> ConversationResponse:  # ← Schema
    """
    Endpoint de conversa com IA.
    """
    response_text = use_case.execute(request.phone, request.text)
    
    return ConversationResponse(
        response=response_text,
        timestamp=datetime.now().isoformat()
    )
```

### 4. HTTP Exceptions

```python
class HTTPException(Exception):
    """Base para exceções HTTP."""
    
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
    
    def to_dict(self) -> dict:
        return {"error": self.detail, "status": self.status_code}

class BadRequest(HTTPException):
    """400 - Requisição inválida."""
    def __init__(self, detail: str):
        super().__init__(400, detail)

class NotFound(HTTPException):
    """404 - Não encontrado."""
    def __init__(self, detail: str):
        super().__init__(404, detail)

class InternalServerError(HTTPException):
    """500 - Erro interno."""
    def __init__(self, detail: str):
        super().__init__(500, detail)
```

### 5. Dependency Injection

```python
# dependencies.py
"""
Dependency Injection Container.

Single place onde concretas implementações são criadas e injetadas.
Rest do código trabalha com abstrações.
"""

def get_checkin_use_case() -> CheckInViaWhatsAppUseCase:
    """
    Factory função para CheckInUseCase.
    
    FastAPI chama isso para cada requisição.
    """
    # Criar banco
    session = SessionLocal()
    
    # Criar implementações concretas
    reservation_repo = ReservationRepositorySQL(session)
    cache_repo = RedisRepository()
    
    # Injetar e retornar
    return CheckInViaWhatsAppUseCase(
        reservation_repository=reservation_repo,
        cache_repository=cache_repo
    )

def get_conversation_use_case() -> ConversationUseCase:
    """Factory para ConversationUseCase."""
    ai_service = OpenAIClient()
    session = SessionLocal()
    reservation_repo = ReservationRepositorySQL(session)
    cache_repository = RedisRepository()
    logger = ConversationLogger()
    
    return ConversationUseCase(
        ai_service=ai_service,
        reservation_repo=reservation_repo,
        cache_repository=cache_repository,
        messaging=None,
        logger=logger
    )

def get_conversation_use_case_memory() -> ConversationUseCase:
    """
    Factory para testes.
    
    Usa implementações em memória, sem dependências externas.
    """
    from tests.unit.mocks.ai_service_mock import AIServiceMock
    
    ai_service = AIServiceMock(responses={})
    reservation_repo = ReservationRepositoryMemory()
    cache_repository = InMemoryCache()
    
    return ConversationUseCase(
        ai_service=ai_service,
        reservation_repo=reservation_repo,
        cache_repository=cache_repository,
        messaging=None,
        logger=None
    )
```

**Diagrama: Interfaces Layer**

```
┌────────────────────────────────────────────────────┐
│         Interfaces Layer                           │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────────────────────────────────────┐     │
│  │  HTTP Endpoints (FastAPI)                │     │
│  │  ├─ POST /webhook/whatsapp               │     │
│  │  ├─ POST /api/conversation               │     │
│  │  ├─ GET  /api/stats                      │     │
│  │  └─ (outros endpoints)                   │     │
│  └──────────────────────────────────────────┘     │
│         ↓ (recebe)                 ↑ (retorna)    │
│         JSON                        JSON           │
│                                                    │
│  ┌──────────────────────────────────────────┐     │
│  │  Schemas (Pydantic - Validação)          │     │
│  │  ├─ CheckInRequest                       │     │
│  │  ├─ CheckInResponse                      │     │
│  │  ├─ ConversationRequest                  │     │
│  │  └─ ConversationResponse                 │     │
│  └──────────────────────────────────────────┘     │
│         ↓ (converte)                ↑             │
│         via Converter                via Converter│
│                                                    │
│  ┌──────────────────────────────────────────┐     │
│  │  Converters (Schema ↔ DTO)               │     │
│  │  ├─ RequestConverters                    │     │
│  │  └─ ResponseConverters                   │     │
│  └──────────────────────────────────────────┘     │
│         ↓ (transforma)              ↑             │
│         DTOs                        DTOs          │
│                                                    │
│  ┌──────────────────────────────────────────┐     │
│  │  Dependencies (DI Container)             │     │
│  │  ├─ get_checkin_use_case()              │     │
│  │  ├─ get_conversation_use_case()         │     │
│  │  └─ get_conversation_use_case_memory()  │     │
│  │     (cria Factory instances)             │     │
│  └──────────────────────────────────────────┘     │
│         ↓ (injeta)                                │
│     Use Cases                                     │
│                                                    │
│  ┌──────────────────────────────────────────┐     │
│  │  HTTP Exceptions                         │     │
│  │  ├─ BadRequest (400)                     │     │
│  │  ├─ NotFound (404)                       │     │
│  │  ├─ InternalServerError (500)            │     │
│  │  └─ (outros status codes)                │     │
│  └──────────────────────────────────────────┘     │
│                                                    │
└────────────────────────────────────────────────────┘
         ↓ (depende)
   Application & Domain Layers
```

---

## 🔄 Fluxos Principais

### 1. Fluxo: Check-in via WhatsApp

**Sequência detalhada:**

```
1. Cliente envia mensagem WhatsApp
   ↓
2. WhatsApp envia POST /webhook/whatsapp
   {
     "phone": "5561999999999",
     "message": "checkin"
   }
   ↓
3. FastAPI recebe e valida com WhatsAppMessage schema
   ↓
4. get_checkin_use_case() injeta dependências
   - SessionLocal() → database connection
   - ReservationRepositorySQL() → implementação SQL
   - RedisRepository() → conecta ao Redis
   ↓
5. Endpoint chama use_case.execute(CheckinRequestDTO)
   ↓
6. Use Case orquestra:
   a) cache_repo.get(phone)
      ├─ Redis.GET "5561999999999"
      └─ Se achado, retorna cached reservation
   
   b) Se não tiver cache:
      ├─ reservation_repo.find_by_phone_number(phone)
      │  ├─ SQL: SELECT * FROM reservations WHERE guest_phone = ?
      │  └─ Retorna Domain Entity (Reservation)
      ├─ reservation.check_in()
      │  └─ Valida invariantes e muda status
      ├─ reservation_repo.save(reservation)
      │  └─ SQL: UPDATE reservations SET status = ?
      └─ cache_repo.set(phone, data, ttl=3600)
         └─ Redis: SET "5561999999999" {...} EX 3600
   ↓
7. Use Case retorna CheckinResponseDTO
   ↓
8. Converter transforma DTO → Schema
   ↓
9. FastAPI retorna JSON
   {
     "message": "✅ Check-in sucesso!",
     "success": true
   }
   ↓
10. JSON vai de volta pra WhatsApp
```

**Diagrama Sequência:**

```
Cliente          WhatsApp           FastAPI         App Layer      Domain   Infrastructure
  │                 │                  │               │             │            │
  ├─ "checkin" ────>│                  │               │             │            │
  │                 ├─ POST /webhook ─>│               │             │            │
  │                 │                  ├─ validate     │             │            │
  │                 │                  ├─ DI inject    │             │            │
  │                 │                  ├─ execute() ──>│             │            │
  │                 │                  │               ├─ cache.get()─────────────>│
  │                 │                  │               │             │            │
  │                 │                  │               │             │    (Redis GET)
  │                 │                  │               │             │            │
  │                 │                  │               │<─ not found ─┤            │
  │                 │                  │               ├─ repo.find()─────────────>│
  │                 │                  │               │             │            │
  │                 │                  │               │             │   (SQL query)
  │                 │                  │               │             │            │
  │                 │                  │               │<─ Reservation ──────────<│
  │                 │                  │               ├─ entity.check_in()       │
  │                 │                  │               ├─ repo.save()──────────────>│
  │                 │                  │               │             │            │
  │                 │                  │               │             │  (SQL UPDATE)
  │                 │                  │               │             │            │
  │                 │                  │               ├─ cache.set()─────────────>│
  │                 │                  │               │             │            │
  │                 │                  │               │             │  (Redis SET)
  │                 │                  │               │             │            │
  │                 │                  │<─ ResponseDTO ┤             │            │
  │                 │                  ├─ converter    │             │            │
  │                 │                  ├─ JSON response            │            │
  │<─────────────────────────────────────────────────────┤            │            │
  │                 │                  │               │             │            │
```

### 2. Fluxo: Conversa Multi-turn com IA

**Sequência detalhada:**

```
1. Cliente envia: "Olá"
   ↓
2. POST /api/conversation com ConversationRequest
   {
     "phone": "5561999999999",
     "text": "Olá"
   }
   ↓
3. get_conversation_use_case() injeta:
   - OpenAIClient() → AI service
   - ReservationRepositorySQL() → banco
   - RedisRepository() → cache
   - ConversationLogger() → logging
   ↓
4. use_case.execute(phone, text)
   ↓
5. Orquestra conversa:
   
   a) _get_conversation_history(phone)
      └─ cache.get("5561999999999")
         └─ Redis GET → returns [{"role":"user", "content":"msg1"}]
   
   b) Convert dicts → Message VOs
      └─ [Message(role="user", content="msg1")]
   
   c) Append user message
      └─ messages.append(Message(role="user", content="Olá"))
   
   d) _call_ai(messages)
      └─ ai_service.chat([{role:user, content:Olá}])
         └─ OpenAI API call
            POST https://api.openai.com/v1/chat/completions
            {
              "model": "gpt-3.5-turbo",
              "messages": [{"role":"user", "content":"Olá"}]
            }
         └─ returns "Oi! Como posso ajudar?"
   
   e) Append assistant response
      └─ messages.append(Message(role="assistant", content="Oi!..."))
   
   f) _update_conversation_history(phone, messages)
      └─ cache.set(phone, messages_dicts, ttl=3600)
         └─ Redis SET com todas as mensagens
   
   g) _log_interaction(phone, user, response)
      └─ logger.log_interaction(...)
         └─ Escreve em logs/conversation_history.json
            {
              "timestamp": "2026-02-21T11:06:45",
              "phone": "5561999999999",
              "user_message": "Olá",
              "ai_response": "Oi! Como posso ajudar?",
              "cost": {"total_usd": 0.000001}
            }
   ↓
6. Retorna resposta "Oi! Como posso ajudar?"
   ↓
7. Converter transforma em ConversationResponse
   ↓
8. FastAPI retorna JSON
   ↓
9. Turn 2: Cliente envia "Qual seu nome?"
   ↓
10. execute(phone, "Qual seu nome?")
    a) get_conversation_history() → [msg1, msg2, assistant_resp1]
    b) Append "Qual seu nome?"
    c) Pass [msg1, ..., msg2, "Qual seu nome?"] to AI
       ← IA tem CONTEXTO de turn 1!
    d) AI responde: "Sou um assistente IA"
    e) history agora tem 6 msgs
    f) Log e return resposta
    ↓
11. Conversa continua com contexto completo!
    ← MULTI-TURN CONVERSATION COM HISTÓRIA
```

**Diagrama Sequência Conversa:**

```
Turn 1:
Cliente: "Olá"
   ↓
Cache: empty
   ↓
AI gets: [{"role":"user","content":"Olá"}]
   ↓
AI returns: "Oi! Bem-vindo!"
   ↓
Cache stored: [msg1_user, msg1_assistant]
   ↓
Logger logged: conversation_history.json entry

Turn 2:
Cliente: "Qual seu nome?"
   ↓
Cache: [msg1_user, msg1_assistant]
   ↓
AI gets: [
    {"role":"user","content":"Olá"},
    {"role":"assistant","content":"Oi! Bem-vindo!"},
    {"role":"user","content":"Qual seu nome?"}  ← NEW
]
   ↓
AI returns: "Meu nome é Assistant. Como posso ajudar?"
   ↓
Cache updated: [msg1_user, msg1_assistant, msg2_user, msg2_assistant]
   ↓
Logger logged: new entry

← AI TEM CONTEXTO!
```

---

## 💉 Dependency Injection (DI)

### Conceito

**DI = Injetar dependências ao invés de criar localmente**

```python
# ❌ BAD - Sem DI (tight coupling)
class CheckInUseCase:
    def __init__(self):
        self.repo = ReservationRepositorySQL()  # ← hardcoded impl
        self.cache = RedisRepository()          # ← hardcoded impl

# Problema: Não posso testar sem SQL real

# ✅ GOOD - Com DI (loose coupling)
class CheckInUseCase:
    def __init__(
        self,
        reservation_repo: ReservationRepository,  # ← abstração
        cache_repo: CacheRepository,              # ← abstração
    ):
        self.repo = reservation_repo
        self.cache = cache_repo

# Agora posso injetar qualquer implementação!
```

### DI Container (dependencies.py)

```python
"""
Single place onde todas as dependências são criadas.

Padrão: Factory Functions
"""

def get_checkin_use_case() -> CheckInViaWhatsAppUseCase:
    """
    Production configuration.
    
    Injeta implementações REAIS.
    """
    session = SessionLocal()
    return CheckInViaWhatsAppUseCase(
        reservation_repository=ReservationRepositorySQL(session),  # Real SQL
        cache_repository=RedisRepository()                          # Real Redis
    )

def get_conversation_use_case_memory() -> ConversationUseCase:
    """
    Test/Development configuration.
    
    Injeta implementações MOCK.
    """
    return ConversationUseCase(
        ai_service=AIServiceMock(responses={}),      # Mock
        reservation_repo=ReservationRepositoryMemory(),  # Memory
        cache_repository=InMemoryCache(),            # Memory
        messaging=None,
        logger=None
    )
```

### FastAPI Dependency Injection

```python
from fastapi import Depends

@router.post("/checkin")
def checkin_endpoint(
    request: CheckInRequest,
    use_case: CheckInViaWhatsAppUseCase = Depends(get_checkin_use_case),
    # ↑ FastAPI automatically calls get_checkin_use_case() and injects result
):
    """FastAPI magic: Depends() calls the factory!"""
    dto = CheckinRequestDTO(phone_number=request.phone_number)
    response_dto = use_case.execute(dto)
    return CheckInResponse(message=response_dto.message, success=True)
```

**Fluxo DI no FastAPI:**

```
HTTP request
    ↓
FastAPI router
    ↓
@router.post with Depends(get_checkin_use_case)
    ↓
FastAPI calls: get_checkin_use_case()
    ├─ SessionLocal()
    ├─ ReservationRepositorySQL(session)
    ├─ RedisRepository()
    └─ CheckInViaWhatsAppUseCase(...) ← injeção!
    ↓
Handler function chamado com use_case injetado
    ↓
Handler executa e retorna
    ↓
HTTP response
```

---

## 🚨 Tratamento de Erros

### 3-Layer Exception Architecture

```
User HTTP Request
    ↓
┌───────────────────────────────────────┐
│ Interfaces Layer                      │
│ - HTTP 400, 404, 500                  │
│ - HTTPException                       │
└──────────────────┬──────────────────┘
                   │ catch & convert
┌───────────────────────────────────────┐
│ Application Layer                     │
│ - ConversationFailed                  │
│ - CheckInFailed                       │
│ - AIServiceError                      │
│ - CacheError                          │
└──────────────────┬──────────────────┘
                   │ catch & convert
┌───────────────────────────────────────┐
│ Domain Layer                          │
│ - DomainException                     │
│ - InvalidCheckInState                 │
│ - InvalidPhoneNumber                  │
│ - InvalidReservationStatus            │
└──────────────────┬──────────────────┘
                   │ core business rules
┌───────────────────────────────────────┐
│ Infrastructure Layer                  │
│ - SQLAlchemy errors                   │
│ - Redis connection errors             │
│ - OpenAI API errors                   │
└───────────────────────────────────────┘
```

### Exemplo: Tratamento de Erro

```python
# Infrastructure (OpenAI)
def chat(self, messages) -> str:
    try:
        response = self.client.chat.completions.create(...)
        return response.choices[0].message.content
    except openai.error.RateLimitError:
        raise AIServiceError("OpenAI rate limit exceeded")
    except openai.error.AuthenticationError:
        raise AIServiceError("OpenAI authentication failed")

# Application (ConversationUseCase)
def execute(self, phone, text) -> str:
    try:
        # ... orchestrate ...
        ai_response = self._call_ai(messages)
        # ... more operations ...
        return ai_response
    except (CacheError, AIServiceError) as e:
        raise ConversationFailed(f"Conversation failed: {str(e)}")

# Interfaces (FastAPI)
@router.post("/api/conversation")
def conversation_endpoint(request: ConversationRequest) -> ConversationResponse:
    try:
        use_case = get_conversation_use_case()
        response = use_case.execute(request.phone, request.text)
        return ConversationResponse(response=response, timestamp=now())
    except ConversationFailed as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ApplicationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## 📊 Diagrama Completo da Arquitetura

```
┌──────────────────────────────────────────────────────────────┐
│                    HTTP Request                              │
│              POST /api/conversation                          │
│          {"phone": "556199999", "text": "Oi"}                │
└─────────────────────────┬──────────────────────────────────┘
                          │
        ┌─────────────────▼──────────────────┐
        │ INTERFACES LAYER                   │
        │ ┌────────────────────────────────┐ │
        │ │ FastAPI Router                 │ │
        │ │ @router.post("/conversation")  │ │
        │ │ - Validates Schema             │ │
        │ │ - Calls Depends(get_conv...)   │ │
        │ └────────┬───────────────────────┘ │
        │          │                         │
        │ ┌────────▼───────────────────────┐ │
        │ │ Dependencies.get_conv_use_case │ │
        │ │ - SQLAlchemy SessionLocal()    │ │
        │ │ - ReservationRepositorySQL()   │ │
        │ │ - RedisRepository()            │ │
        │ │ - OpenAIClient()               │ │
        │ │ - ConversationLogger()         │ │
        │ │ - Returns ConversationUseCase  │ │
        │ └────────┬───────────────────────┘ │
        │          │                         │
        │ ┌────────▼───────────────────────┐ │
        │ │ Converters                     │ │
        │ │ Schema → DTO                   │ │
        │ └────────┬───────────────────────┘ │
        └─────────────────────┬──────────────┘
                              │
        ┌─────────────────────▼──────────────────┐
        │ APPLICATION LAYER                      │
        │ ┌────────────────────────────────────┐ │
        │ │ ConversationUseCase.execute()      │ │
        │ │                                    │ │
        │ │ 1. _get_conversation_history()    │ │
        │ │    └─ calls cache_repo.get()       │ │
        │ │                                    │ │
        │ │ 2. Convert dicts → Message VOs    │ │
        │ │    (Domain layer validation)      │ │
        │ │                                    │ │
        │ │ 3. Append new Message VO          │ │
        │ │                                    │ │
        │ │ 4. _call_ai(messages)             │ │
        │ │    └─ calls ai_service.chat()     │ │
        │ │                                    │ │
        │ │ 5. _update_conversation_history() │ │
        │ │    └─ calls cache_repo.set()      │ │
        │ │                                    │ │
        │ │ 6. _log_interaction()             │ │
        │ │    └─ calls logger.log_inter()    │ │
        │ │                                    │ │
        │ │ 7. Return ai_response text        │ │
        │ └────────────────────────────────────┘ │
        └──────────────────┬─────────────────────┘
                           │
    ┌──────────────────────┴───────────────────────┐
    │                                              │
    │                                              │
┌───▼──────────────────┐      ┌────────────────────▼───┐
│ DOMAIN LAYER         │      │ INFRASTRUCTURE LAYER   │
├──────────────────────┤      ├────────────────────────┤
│ Message (VO)         │      │                        │
│ - role               │      │ ReservationRepositorySQL
│ - content            │      │ - session              │
│ - is_valid()         │      │ - query SQL            │
│                      │      │ - returns Entity       │
│ Entities passed      │      │                        │
│ to Use Case →        │      │ RedisRepository        │
│ Use Case calls       │      │ - redis client         │
│ methods on entities  │      │ - GET/SET in Redis     │
│ Entities validate    │      │                        │
│ invariants on        │      │ OpenAIClient           │
│ construction         │      │ - LLM calls            │
│                      │      │ - GPT-3.5-turbo        │
│ Repositories are     │      │                        │
│ INTERFACES here      │      │ ConversationLogger     │
│ (not implementations)│      │ - JSON file writing    │
│                      │      │                        │
│ Exceptions raised    │      │ Database               │
│ when invariants      │      │ - PostgreSQL conn      │
│ broken               │      │ - SQL queries execute  │
└──────────────────────┘      │                        │
                              │ External APIs         │
                              │ - OpenAI gpt-3.5-turbo│
                              │ - Redis Cloud         │
                              │ - PostgreSQL          │
                              └────────────────────────┘
```

---

## 🎯 Resumo: O que Mude sem Quebrar Clean Arch?

### ✅ Você PODE trocar sem quebrar NADA:

```
ReservationRepositorySQL   ← trocar por ReservationRepositoryMongo
                            sem afetar Use Cases, Entities, etc.

RedisRepository           ← trocar por MemcachedRepository
                            mudando só Infrastructure

OpenAIClient              ← trocar por AnthropicClient
                            implementando AIService

FastAPI webhoo←           ← trocar por Flask, Django
                            endpoints (Interfaces)

PostgreSQL ←              ← trocar por MySQL, SQLite
                            no .env apenas
```

### ❌ Você NÃO deve mexer em:

```
Domain layer logic        ← Reservation.check_in() invariantes
                            NUNCA devem mudar por motivos técnicos

Message VO invariantes    ← role e content validação
                            NUNCA devem ser removidas

Repository interfaces     ← ReservationRepository, CacheRepository
                            contrato do domínio
```

---

## 🚀 Para Evoluir Mantendo Clean Architecture:

### Adicionar Nova Use Case

```python
# 1. Define no Domain (entities, VOs, interfaces)
# 2. Create em Application/use_cases/nova_use_case.py
class NovaUseCase:
    def __init__(
        self,
        repository: SomeRepository,  # ← Interface do Domain
        service: SomeService,        # ← Interface do Domain
    ):
        ...
    
    def execute(self, input_dto: InputDTO) -> OutputDTO:
        # Orquestra entidades
        entity = self.repository.find(...)
        entity.metodo_dominio()
        self.repository.save(entity)
        return OutputDTO(...)

# 3. Adicione ao DI (dependencies.py)
def get_nova_use_case():
    return NovaUseCase(
        repository=SomeRepositorySQL(),
        service=SomeServiceImpl()
    )

# 4. Create Endpoint em Interfaces/api
@router.post("/api/nova")
def nova_endpoint(
    req: NovaSchema,
    use_case: NovaUseCase = Depends(get_nova_use_case)
):
    dto = RequestConverter.to_dto(req)
    result_dto = use_case.execute(dto)
    return ResponseConverter.to_schema(result_dto)
```

### Adicionar Nova Entity

```python
# 1. Define Entity em Domain/entities/
class NovaEntity:
    def __init__(self, ...):
        self.id = ...
        self.attr1 = ...
    
    def metodo_dominio(self):
        # validações, invariantes
        pass

# 2. Create Repository interface em Domain/repositories/
class NovaEntityRepository(ABC):
    @abstractmethod
    def save(self, entity: NovaEntity): pass
    @abstractmethod
    def find_by_id(self, id): pass

# 3. Implementa em Infrastructure
class NovaEntityRepositorySQL(NovaEntityRepository):
    def save(self, entity): ...
    def find_by_id(self, id): ...

# 4. Injeta em Use Cases
class SomeUseCase:
    def __init__(self, nova_repo: NovaEntityRepository):
        ...
```

---

## 📚 Referências

- **Clean Architecture:** Martin, Robert C. "Clean Architecture"
- **Domain-Driven Design:** Evans, Eric. "Domain-Driven Design"
- **SOLID Principles:** Various
- **Repository Pattern:** Fowler, Martin
- **Value Objects:** DDD pattern
- **FastAPI:** https://fastapi.tiangolo.com/
- **SQLAlchemy:** https://www.sqlalchemy.org/
- **Pydantic:** https://docs.pydantic.dev/

---

**Última atualização:** 21 de Fevereiro de 2026
