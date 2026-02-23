# ✅ Clean Architecture Refactor - Completo

## 📋 O que foi corrigido

### 1️⃣ **Message Value Object** ✨
**Arquivo novo:** `app/domain/value_objects/message.py`

Antes: Strings soltas `{"role": "user", "content": "..."}` espalhadas no código
Depois: VO tipado com validações de invariante

```python
from app.domain.value_objects.message import Message

# ✅ Correto: criação com validação
msg = Message(role="user", content="Olá")
msg.to_dict()  # {"role": "user", "content": "Olá"}

# ❌ Levanta exceção: validação de invariante
msg = Message(role="invalid", content="...")  # ValueError!
msg = Message(role="user", content="")  # ValueError! vazio não é permitido
```

**Benefícios:**
- Type safety
- Invariantes garantidas em tempo de criação
- Método `to_dict()` para serialização
- Equidade entre Messages

---

### 2️⃣ **Cache Repository Interface** 📋
**Arquivo novo:** `app/domain/repositories/cache_repository.py`

Antes: RedisRepository sem contrato formal
Depois: Interface abstrata no Domain

```python
from app.domain.repositories import CacheRepository

class CacheRepository(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]: pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None: pass
    
    # ... outros métodos
```

**Implementações:**
- `app/infrastructure/cache/redis_repository.py` - Produção
- `InMemoryCache` em `dependencies.py` - Testes

**Benefícios:**
- Contrato formal definido no Domain
- Múltiplas implementações suportadas
- Fácil testar com mock

---

### 3️⃣ **Camada de Exceções Estruturada** 🚨
**Arquivos novos:**
- `app/domain/exceptions.py` - Violações de regras de negócio
- `app/application/exceptions.py` - Falhas de orquestração
- `app/interfaces/exceptions.py` - Erros HTTP

```python
# Domain: regra de negócio violada
class InvalidPhoneNumber(DomainException): pass

# Application: processo falhou
class ConversationFailed(ApplicationException): pass

# Interfaces: precisa converter para HTTP
class BadRequest(APIException):
    def __init__(self, message):
        super().__init__(message, status_code=400)
```

**Como usar:**
```python
from app.application.exceptions import ConversationFailed

try:
    response = use_case.execute(phone, text)
except ConversationFailed as e:
    return {"error": "Conversation failed", "details": str(e)}, 500
```

**Benefícios:**
- Separação clara de responsabilidades
- Fácil tratar erros apropriadamente
- HTTP status codes corretos

---

### 4️⃣ **DTOs vs Schemas** 📦
**Arquivo novo:** `app/interfaces/schemas.py`

Antes: Mesmos DTOs para HTTP e comunicação interna
Depois: Separação clara

```
HTTP Request → Pydantic Schema → Converter → Application DTO → Use-case
Response ← Pydantic Schema ← Converter ← Application DTO ← Use-case
```

**Schemas (Pydantic - Interfaces):**
```python
# app/interfaces/schemas.py
class WhatsAppMessageRequest(BaseModel):
    phone: str = Field(..., min_length=10)
    message: str = Field(..., max_length=2000)
```

**DTOs (Application):**
```python
# app/application/dto/
class CheckinRequestDTO:
    def __init__(self, phone: str):
        self.phone_number = phone
```

**Converters:**
```python
# app/interfaces/converters.py
class RequestConverters:
    @staticmethod
    def whatsapp_to_conversation_dto(req: WhatsAppMessageRequest):
        return {"phone": req.phone, "message": req.message}
```

**Benefícios:**
- Schemas validam HTTP com Pydantic
- DTOs são apenas data containers
- Converters deixa fronteira clara

---

### 5️⃣ **Conversation Use-Case Refatorado** 🚀
**Arquivo atualizado:** `app/application/use_cases/conversation.py`

Antes:
```python
messages = history + [{"role": "user", "content": text}]
answer = ai_resp["choices"][0]["message"]["content"]
```

Depois:
```python
messages = [Message(role=msg["role"], content=msg["content"]) for msg in history]
user_msg = Message(role="user", content=text)
messages.append(user_msg)

response = self._call_ai(messages)
```

**Melhorias:**
- Usa `Message` VO para type safety
- Métodos privados bem documentados
- Tratamento de erros robusto
- Suporta múltiplos formatos de resposta AI

---

### 6️⃣ **Redis Repository Melhorado** 🔴
**Arquivo atualizado:** `app/infrastructure/cache/redis_repository.py`

Antes:
```python
class RedisRepository(ConversationCacheRepository):
    def __init__(self, host='...', port=10759):
        # hardcoded
```

Depois:
```python
class RedisRepository(CacheRepository):
    def __init__(self, host=None, port=None, ...):
        self.host = host or os.getenv("REDIS_HOST")
        self.port = port or int(os.getenv("REDIS_PORT"))
        # Todos os métodos documentados
        # Tratamento de erro robusto
```

**Novos métodos:**
- `delete(key)` - Deletar chave
- `exists(key)` - Verificar existência
- `clear()` - Limpar tudo

**Benefícios:**
- Configuração via env vars
- Interface completa
- Erro handling robusto

---

### 7️⃣ **Dependency Injection Melhorado** 💉
**Arquivo atualizado:** `app/interfaces/dependencies.py`

Agora tem 3 funções:
- `get_checkin_use_case()` - Produção
- `get_conversation_use_case()` - Produção
- `get_conversation_use_case_memory()` - Testes/Dev

```python
def get_conversation_use_case() -> ConversationUseCase:
    """Get production instance with real services."""
    ai_service = OpenAIClient()  # Real OpenAI
    cache = RedisRepository()     # Real Redis
    repo = ReservationRepositorySQL()
    return ConversationUseCase(ai_service, repo, cache)

def get_conversation_use_case_memory() -> ConversationUseCase:
    """Get test instance with in-memory services."""
    ai_service = AIServiceMock()  # Mock
    cache = InMemoryCache()       # In-memory
    repo = ReservationRepositoryMemory()
    return ConversationUseCase(ai_service, repo, cache)
```

**Benefícios:**
- Fácil switch entre prod/test
- Todas as dependências em um lugar
- Type hints corretos

---

## 🏗️ Arquitetura Resultante

```
┌─────────────────────────────────────────────────────┐
│           INTERFACES (Web/API/External)             │
│  • whatsapp_webhook.py (Pydantic Schemas)           │
│  • schemas.py (APIs request/response)               │
│  • exceptions.py (APIException, BadRequest, ...)    │
│  • converters.py (Schema ↔️ DTO)                     │
│  • dependencies.py (Composition Root)               │
└─────────────────────────────────────────────────────┘
                        ↓ ↑
              (DTOs - Data Transfer)
                        ↓ ↑
┌─────────────────────────────────────────────────────┐
│           APPLICATION (Business Logic)              │
│  • use_cases/*.py (Orchestration)                   │
│  • services/*.py (AIService interface)              │
│  • dto/*.py (Data Transfer Objects)                 │
│  • exceptions.py (ApplicationException, ...)        │
└─────────────────────────────────────────────────────┘
                        ↓ ↑
            (Domain Interfaces abstração)
                        ↓ ↑
┌─────────────────────────────────────────────────────┐
│              DOMAIN (Entities/Rules)                │
│  • entities/*.py (Reservation, ...)                 │
│  • value_objects/*.py (PhoneNumber, Message)        │
│  • enums/*.py (ReservationStatus, ...)              │
│  • repositories/*.py (CacheRepository, ...)         │
│  • services/*.py (AIService interface)              │
│  • exceptions.py (DomainException, ...)             │
└─────────────────────────────────────────────────────┘
                        ↓ ↑
         (Concretos implementam abstrações)
                        ↓ ↑
┌─────────────────────────────────────────────────────┐
│         INFRASTRUCTURE (Implementations)            │
│  • persistence/sql/*.py (ReservationRepositorySQL)  │
│  • persistence/memory/*.py (ReservationRepositoryMemory) │
│  • cache/redis_repository.py (RedisRepository)      │
│  • ai/openai_client.py (OpenAIClient)               │
└─────────────────────────────────────────────────────┘
```

---

## 📊 Checklist de Clean Architecture

| Princípio | Status | Evidência |
|-----------|--------|-----------|
| **Dependency Rule** | ✅ | Camadas internas não conhecem externas |
| **Interfaces** | ✅ | `CacheRepository`, `AIService`, `ReservationRepository` no Domain |
| **Value Objects** | ✅ | `Message`, `PhoneNumber` com invariantes |
| **Use Cases** | ✅ | Orquestração sem conhecer implementação |
| **DTOs** | ✅ | Separadas de Schemas e Entities |
| **Exceções** | ✅ | 3 níveis com mapeamento correto |
| **Sem lógica em DTO** | ✅ | DTOs são apenas containers |
| **Injeção de Dependência** | ✅ | Composição centralizada em `dependencies.py` |
| **Entities** | ✅ | Puro, sem frameworks `Reservation` |
| **Repository Pattern** | ✅ | Abstrações implementadas em Infrastructure |

---

## 🧪 Como Testar

```powershell
# Teste com mocks (sem Redis/OpenAI)
py test_conversation_mock.py

# Teste com OpenAI real (precisa de saldo)
py test_real_chat.py

# Rodar testes unitários
py -m pytest tests/unit/ -v
```

---

## 🎯 Próximas Melhorias (Futuro)

- [ ] Event Bus para logging/eventos distribuídos
- [ ] Domain Events (`ReservationCheckedInEvent`, etc)
- [ ] Logger centralizado
- [ ] Specification pattern para queries complexas
- [ ] Anti-corruption layer para APIs externas
- [ ] CQRS para separar leitura/escrita

---

## 📚 Referências

- Robert C. Martin - Clean Architecture
- Domain-Driven Design - Eric Evans
- Patterns of Enterprise Application Architecture - Martin Fowler
