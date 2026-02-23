# 🚀 Quick Start: Meta WhatsApp API Integrado

**Status:** Código 100% integrado ✅  
**Tempo para funcionar:** 10-15 minutos  
**O que você vai fazer:** Setup local + testar envio/recebimento

---

## 📋 Pré-Requisitos

```
✅ Sua conta Meta com acesso à console
✅ App criado
✅ Forma de pagamento configurada (important!)
✅ Número de teste adicionado
✅ FastAPI rodando
✅ ngrok instalado (para tunnel local)
```

---

## 🎯 Passo 1: Coletando Credenciais

### A. Vá em Meta Console

```
https://developers.facebook.com/
```

### B. Seu App → WhatsApp → API Setup

**Copie essas informações:**

| Item | Valor | Onde encontrar |
|------|-------|----------------|
| **Access Token** | EAABs... | "Copy Token" button |
| **Phone Number ID** | 101652038203517 | "Phone Number ID" field |
| **Seu Número de Teste** | +55 61 99877 6092 | "Phone Number" dropdown |

---

## 🎯 Passo 2: Configurar .env

### A. Abre o arquivo `.env` na raiz do projeto

```bash
cd e:\Desenvolvimento\hotel-automation
```

### B. Coloca essas variáveis (copiar dos campos acima):

```env
# Meta WhatsApp
META_ACCESS_TOKEN=EAABs...seu_token_exato_aqui...
PHONE_NUMBER_ID=101652038203517
WEBHOOK_VERIFY_TOKEN=meu_token_super_secreto_123

# Database (já deve ter)
DATABASE_URL=...

# Redis (já deve ter)
REDIS_URL=...

# OpenAI (já deve ter)
OPENAI_API_KEY=...
```

### C. IMPORTANTE

```
⚠️ NÃO coloca espaços extras!
⚠️ Token é CASE-SENSITIVE
⚠️ Salva o arquivo (Ctrl+S)
```

---

## 🎯 Passo 3: Instalar Dependências

```bash
pip install -r requirements.txt
```

Vai instalar: `requests` (faltava!)

---

## 🎯 Passo 4: Testar Envio (Local)

### A. Abre Terminal

```bash
# Na pasta do projeto
cd e:\Desenvolvimento\hotel-automation
```

### B. Roda o script de teste

```bash
python test_whatsapp_meta.py
```

### C. Esperado

```
============================================================
TEST 1: Testar Conexão com Meta API
============================================================
✅ Cliente WhatsApp inicializado
✅ Conexão com Meta API OK!

============================================================
TEST 2: Enviar Mensagem de Texto
============================================================
✅ Mensagem enviada! ID: wamid.xxx
📱 Verifique seu WhatsApp em alguns segundos...
```

### D. Verifique seu WhatsApp! 📱

```
Você deveria receber uma mensagem tipo:
"Olá! Essa é uma mensagem de teste do WhatsApp API Meta 🚀"
```

---

## 🎯 Passo 5: Configurar Webhook (Para Receber)

Se o **envio funcionou**, agora configura recebimento.

### A. Instala ngrok

```bash
# Download: https://ngrok.com/download
# Deszip em um local
# Ou use chocolatey:

choco install ngrok
```

### B. Abre 1º Terminal (ngrok)

```bash
ngrok http 8000
```

**Resultado:**
```
Forwarding https://1234abc.ngrok.io -> http://localhost:8000
```

**Copia a URL:** `https://1234abc.ngrok.io`

### C. Abre 2º Terminal (FastAPI)

```bash
cd e:\Desenvolvimento\hotel-automation
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Esperado:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### D. Configura Webhook no Meta

```
https://developers.facebook.com/
↓
Seu App
↓
Configuração  (left sidebar)
↓
Webhooks
↓
Editar Webhook
```

**Preencha com:**

| Campo | Valor |
|-------|-------|
| **Callback URL** | `https://1234abc.ngrok.io/webhook/whatsapp` |
| **Verify Token** | `meu_token_super_secreto_123` (mesmo do .env) |
| **Clica** | "Verificação" |

**Esperado nos logs do FastAPI:**
```
🔐 Webhook verification request: mode=subscribe, token_match=True
✅ Webhook verificado com sucesso!
```

---

## 🎯 Passo 6: Testar Recebimento

### A. Seu Celular

```
Abre WhatsApp
↓
Procura o número de teste (Meta forneceu)
↓
Envia uma mensagem: "Olá!"
```

### B. Logs do FastAPI (2º Terminal)

**Esperado:**
```
📨 Webhook recebido: {...}
📱 Mensagem de 5561998776092 | tipo: text | id: wamid.xxx
✅ Mensagem marcada como lida
📝 Conteúdo: 'Olá!'
✅ Resposta enviada para 5561998776092
```

### C. Seu Celular Recebe Resposta

```
Você vê:
"Recebi sua mensagem: 'Olá!'

Como posso ajudar?"
```

---

## ✅ Se Tudo Funcionou!

```
✅ Envio funciona
✅ Recebimento funciona
✅ Respostas automáticas funcionam
✅ VOCÊ PRONTO PARA PRODUÇÃO! 🎉
```

---

## ❌ Se Algo Não Funcionar

### Problema: "Conexão recusada" ou "Unauthorized"

```
Causas:
├─ Token expirou (60 dias)
├─ Token está errado
├─ Phone ID está errado
└─ Forma de pagamento não confirmada

Solução:
├─ Gera novo token em Meta
├─ Copia exatamente (sem espaços)
├─ Verifica Phone ID é tipo: 101652038203517
└─ Confirma forma de pagamento na console
```

### Problema: "Mensagem não chega no WhatsApp"

```
Causas:
├─ Número está errado ou incompleto
├─ Webhook não foi verificado
├─ Formato do número inválido (sem código país)
└─ Conta suspensa por abuso

Solução:
├─ Número deve ser: 5561998776092 (sem +, sem -)
├─ Check logs: "Webhook verificado com sucesso!"
├─ Usa _format_phone() que já formata
└─ Aguarda uns 60 segundos entre mensagens
```

### Problema: "Webhook verification falhou"

```
Causas:
├─ Verify Token está errado no Meta
├─ Token no .env é diferente
├─ URL pública (ngrok) mudou
└─ Timeout na requisição

Solução:
├─ Copia .env novamente (exatamente igual)
├─ Reinicia ngrok (novo URL)
├─ Cola novo URL em Meta
├─ Tenta Verificação novamente
```

---

## 📚 Próximos Passos

### 1. Integrar com sua IA (OpenAI)

Atualize `_generate_reply()` em `whatsapp_webhook.py`:

```python
async def _generate_reply(from_phone: str, content: str, use_case) -> str:
    # Em vez de resposta simples:
    # -  Chama sua IA para gerar resposta
    # - Processa com use cases
```

### 2. Fluxo de Reserva

```
Usuário: "Quero fazer uma reserva"
         ↓
App: "Qual a data de chegada?"
         ↓
Usuário: "21 de fevereiro"
         ↓
App: "Quantos quartos?"
         ↓
Usuário: "2"
         ↓
App: "Ok, reserva criada! Link de pagamento: ..."
```

### 3. Adicionar Stripe

Depois de WhatsApp 100% funcionando:

```python
# Em send_payment_link():
payment_link = create_stripe_link(reservation)
client.send_text_message(phone, f"Pague aqui: {payment_link}")
```

---

## 📞 Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| `ConnectionError` | Verifica internet, token expirou? |
| `400 Invalid recipient` | Número sem código país: adiciona "55" |
| `403 Unauthorized` | Token inválido, gera novo |
| `429 Rate limited` | Aguarda 1 min antes de enviar de novo |
| Webhook não verifica | Token no Meta ≠ Token no .env |
| Mensagem não chega | Número não é test contact |

---

## 🎊 Você Está Pronto!

Seu projeto agora tem:

```
✅ Cliente Meta WhatsApp (classes prontas)
✅ Webhook de recebimento (verifica + processa)
✅ Envio de mensagens (texto, botões, listas)
✅ Teste local completo
✅ .env exemplo com variáveis
```

**Próximo passo:** 
- ⏳ Integrar IA (OpenAI)
- ⏳ Integrar Payment (Stripe)  
- ⏳ Deploy em produção

🚀 **Você tem um MVP pronto para primeiro cliente!**
