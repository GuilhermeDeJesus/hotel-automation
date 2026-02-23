# 📊 Como Acessar Histórico de Requisições OpenAI

## 3 Formas de Ver Seu Histórico

### 🥇 **FORMA 1: Dashboard Web OpenAI (MAIS FÁCIL)**

#### Links Diretos:

1. **Ver Uso Detalhado por Data**
   ```
   https://platform.openai.com/account/usage/overview
   ```
   - Data/hora de cada requisição
   - Modelo usado
   - Tokens gastos (entrada/saída)
   - Custo em dólares
   - ⏰ Atualiza a cada 5-10 minutos

2. **Ver Faturamento**
   ```
   https://platform.openai.com/account/billing/history
   ```
   - Transações de cobrança
   - Saldo do mês
   - Histórico de pagamentos

3. **Ver de Forma Detalhada**
   ```
   https://platform.openai.com/account/usage/detailed
   ```
   - Breakdown por hora
   - Por modelo
   - Por tipo de operação

#### ⚠️ Importante:
- OpenAI **NÃO mostra o conteúdo das mensagens** (privado)
- Você vê apenas: data, hora, modelo, tokens, custo
- Leva alguns minutos para atualizar
- É a forma mais confiável

---

### 🥈 **FORMA 2: Seu Próprio Log (RECOMENDADO PARA APP)**

Implementamos um logger que salva TUDO localmente!

#### Como Usar:

1. **Integrar no seu ConversationUseCase:**
   ```python
   from app.infrastructure.logging.conversation_logger import ConversationLogger
   
   logger = ConversationLogger()
   
   # Após cada conversa, registrar:
   logger.log_interaction(
       phone="5511999999999",
       user_message="Olá",
       ai_response="Bem-vindо!",
       tokens_input=10,
       tokens_output=15,
       model="gpt-3.5-turbo"
   )
   ```

2. **Ver histórico gravado:**
   ```powershell
   py view_conversation_history.py
   ```
   
   Menu interativo com:
   - 📊 Estatísticas gerais
   - 📝 Últimas conversas
   - 🔍 Buscar por phone
   - 📅 Buscar por data
   - 📥 Exportar para CSV

3. **Estatísticas em Tempo Real:**
   ```python
   logger = ConversationLogger()
   stats = logger.get_stats()
   
   print(f"Total: {stats['total_interactions']} conversas")
   print(f"Custo: ${stats['total_cost_usd']}")
   print(f"Tokens: {stats['total_tokens']}")
   ```

#### Arquivo de Dados:
```
logs/conversation_history.json
```

Contém:
```json
[
  {
    "id": 1,
    "timestamp": "2026-02-21T14:30:45.123456",
    "date": "2026-02-21",
    "time": "14:30:45",
    "phone": "5511999999999",
    "user_message": "Olá, preciso de check-in",
    "ai_response": "Bem-vindo ao hotel! Como posso ajudar?",
    "model": "gpt-3.5-turbo",
    "tokens": {
      "input": 12,
      "output": 18,
      "total": 30
    },
    "cost": {
      "input_usd": 0.000006,
      "output_usd": 0.000027,
      "total_usd": 0.000033
    },
    "metadata": {"source": "whatsapp"}
  }
]
```

---

### 🥉 **FORMA 3: Via CLI OpenAI**

Se tiver instalado o CLI:

```powershell
# Listar histórico
openai api models.list

# Ver uso
curl https://api.openai.com/v1/usage/tokens \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

⚠️ **Nota:** OpenAI removeu a API de histórico completo por privacidade. O dashboard é a forma oficial.

---

## 📊 Comparativo das 3 Formas

| Forma | Acesso | Dados Visíveis | Atualização | Privacidade |
|-------|--------|---|---|---|
| **Dashboard Web** | Rápido | Custo, tokens, hora | 5-10 min | ✅ Protegido |
| **Seu Log Local** | Local | TUDO (completo) | ⏱️ Real-time | ✅ Total controle |
| **Via CLI** | Técnico | Limitado | ⏱️ Real-time | ✅ Protegido |

---

## 🚀 Implementar Logger no Seu Projeto

### 1. Atualizar ConversationUseCase

```python
from app.infrastructure.logging.conversation_logger import ConversationLogger

class ConversationUseCase:
    def __init__(self, ..., logger: ConversationLogger = None):
        self.logger = logger or ConversationLogger()
    
    def execute(self, phone: str, text: str) -> str:
        # ... código existente ...
        
        # Registrar após sucesso
        self.logger.log_interaction(
            phone=phone,
            user_message=text,
            ai_response=response,
            tokens_input=input_tokens,
            tokens_output=output_tokens,
            model="gpt-3.5-turbo",
            metadata={"source": "whatsapp"}
        )
        
        return response
```

### 2. Na Dependency Injection

```python
from app.infrastructure.logging.conversation_logger import ConversationLogger

def get_conversation_use_case():
    logger = ConversationLogger()
    # ... resto do código ...
    return ConversationUseCase(
        ...,
        logger=logger
    )
```

### 3. Visualizar Depois

```powershell
# Menu interativo
py view_conversation_history.py

# Ou programaticamente
from app.infrastructure.logging.conversation_logger import ConversationLogger

logger = ConversationLogger()
logger.print_stats()
logger.print_recent(10)

# Exportar para análise
logger.export_csv("relatorio_conversas.csv")
```

---

## 📈 Exemplos de Uso

### Ver Custos por Data

```python
logger = ConversationLogger()

# Conversas de hoje
today = datetime.now().strftime("%Y-%m-%d")
conversations = logger.get_by_date(today)

total_cost = sum(c['cost']['total_usd'] for c in conversations)
print(f"Gasto hoje: ${total_cost:.4f}")
```

### Ver Custos por Usuário

```python
logger = ConversationLogger()

# Todas as conversas de um phone
phone_convs = logger.get_by_phone("5511999999999")

total = sum(c['cost']['total_usd'] for c in phone_convs)
print(f"Gasto do cliente: ${total:.4f}")
```

### Auditoria por Período

```python
logger = ConversationLogger()

# Conversas de 1 semana
conversas = logger.get_by_date_range("2026-02-15", "2026-02-21")

print(f"Semana usou {len(conversas)} conversas")
print(f"Custo: ${sum(c['cost']['total_usd'] for c in conversas):.4f}")
```

---

## 🎯 Recomendação Final

**Use a combinação:**

1. ✅ **Dashboard OpenAI** para ver estatísticas oficiais (verificação)
2. ✅ **Seu Logger Local** para auditoria interna e análise
3. ✅ **Arquivo JSON** como backup de dados

Assim você tem:
- 📊 Dados completos e verificáveis
- 🔒 Controle total / privacidade
- 📈 Análises detalhadas
- 🛡️ Auditoria e compliance

---

## 🔗 Links Rápidos

```
📊 Dashboard:     https://platform.openai.com/account/usage/overview
💳 Billing:       https://platform.openai.com/account/billing/overview
🔑 API Keys:      https://platform.openai.com/api-keys
📚 Docs:          https://platform.openai.com/docs/guides/tokens
```

---

**Quer ajuda para integrar o logger no seu projeto?** 💡
