## 🚀 Como Usar o Script de Conversa Interativa

### ✅ Pré-requisitos

1. **Python 3.14** com pacotes instalados
2. **OPENAI_API_KEY** configurada no `.env` com saldo disponível
3. Terminais permitem entrada via pipe (comando: `@"..input.."@ | py scripts/...`)

### 📝 Executar

**IMPORTANTE: Use `py` (não `python`)**

```powershell
# Execução interativa direta
py scripts/interactive_conversation.py

# Executar com entrada piped (para testes)
@"
Olá, como você está?
exit
"@ | py scripts/interactive_conversation.py
```

### ⚠️ Possíveis Erros

#### 1. **ModuleNotFoundError: No module named 'dotenv'**
```
❌ Possível Causa: Usando `python` (MSYS) em vez de `py` (Python 3.14)
✅ Solução: Use `py scripts/interactive_conversation.py`
```

#### 2. **Error code: 429 - insufficient_quota**
```
❌ Possível Causa: Chave OpenAI sem saldo/crédito
✅ Solução: 
   a) Adicione crédito em https://platform.openai.com/account/billing/overview
   b) Ou configure OPENAI_API_KEY=sk-xxxxx com outra chave ativa
```

#### 3. **EOF when reading a line**
```
❌ Causa: Terminal sem entrada interativa real
✅ Solução: Use comando piped com @"..."@ no PowerShell
```

### 📊 Testes Sem Saldo OpenAI

Se sua chave não tem crédito, execute os testes com mocks:

```powershell
# Teste com mocks (sem chamar API real)
py test_conversation_mock.py

# Teste de integração OpenAI (requer saldo)
py test_openai_simple.py
```

### 🔍 Estrutura dos Scripts

- **`scripts/interactive_conversation.py`** - Script interativo com OpenAI
- **`test_conversation_mock.py`** - Teste com mocks (sem API)
- **`test_openai_simple.py`** - Teste de integração (requer saldo)

### 🐛 Debug

Se ainda houver problemas, verifique:

```powershell
# Python correto?
py --version  # Deve ser 3.14.x

# Dotenv instalado?
py -m pip show python-dotenv

# OpenAI atualizado?
py -m pip show openai  # Deve ser 2.x

# Variáveis de ambiente?
py -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API Key:', os.getenv('OPENAI_API_KEY')[:10] + '...' if os.getenv('OPENAI_API_KEY') else 'NOT SET')"
```

### 💡 Resumo da Correção

1. **Adicionado suporte para OpenAI SDK v2.x** no `app/infrastructure/ai/openai_client.py`:
   - Usa `openai.OpenAI(api_key)` em vez de `openai.api_key = key`
   - Usa `client.chat.completions.create()` em vez de `ChatCompletion.create()`

2. **Corrigido Python path** em todos os scripts:
   - `sys.path.insert(0, ...)` para encontrar módulo `app`
   - Validação para evitar usar MSYS Python

3. **Atualizado `requirements.txt`**: Confirma instalação de `python-dotenv` e `openai`
