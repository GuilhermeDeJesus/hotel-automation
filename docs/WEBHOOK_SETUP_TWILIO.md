# 🚀 Setup Webhook Twilio WhatsApp

**Status:** Ready to test ✅  
**Tempo setup:** 10 minutos  
**Custo:** $0 (usando sandbox)

---

## 📋 O que é Webhook?

```
Usuário: "Oi" → Twilio Sandbox (+1 415 523 8886)
         ↓
Twilio: "Recebi uma mensagem!"
         ↓
Twilio chama seu endpoint: POST /webhook/whatsapp/twilio
         ↓
Seu Bot: Processa a mensagem
         ↓
Bot: "Olá! Como posso ajudar?"
         ↓
Twilio envia resposta pro usuário
```

---

## 🎯 Passo 1: Inicie o FastAPI

Abra um terminal e rode:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Esperado:**
```
Uvicorn running on http://0.0.0.0:8000
```

---

## 🎯 Passo 2: Instale ngrok

O ngrok expõe seu localhost para a internet (Twilio conseguir chamar seu PC).

### Windows:

```bash
# 1. Download
https://ngrok.com/download

# 2. Descompacte em C:\ngrok\

# 3. Abra novo PowerShell e rode:
cd C:\ngrok
.\ngrok.exe http 8000
```

### macOS/Linux:

```bash
# 1. Install
brew install ngrok

# 2. Rode:
ngrok http 8000
```

---

## 🎯 Passo 3: Copie a URL do ngrok

Quando rodar o ngrok, você verá algo assim:

```
ngrok                                                       (Ctrl+C to quit)

Session Status                online
Account                       <sua-conta>
Version                        3.3.0
Region                         us
Latency                        15ms
Web Interface                  http://127.0.0.1:4040

Forwarding                     https://abc123.ngrok.io -> http://localhost:8000
```

**Copie:** `https://abc123.ngrok.io`

(As aspas e número mudam cada vez que você roda)

---

## 🎯 Passo 4: Configure no Twilio Console

### A. Acesse
```
https://www.twilio.com/console/sms/whatsapp/sandbox
```

### B. Procure por "Webhook Settings"

Desça a página até encontrar a seção **"When a message comes in"**:

```
┌─────────────────────────────────────┐
│ When a message comes in             │
├─────────────────────────────────────┤
│                                     │
│ [URL input field]                   │
│ https://seu-ngrok-url/...           │
│                                     │
│ [Dropdown: HTTP POST]               │
│                                     │
│ [Save]                              │
│                                     │
└─────────────────────────────────────┘
```

### C. Cole a URL do webhook

```
https://abc123.ngrok.io/webhook/whatsapp/twilio
```

**Importante:** Termina em `/webhook/whatsapp/twilio` (Twilio, não Meta!)

### D. Deixe "HTTP POST" selecionado

### E. Clique em "Save"

---

## 🎯 Passo 5: Teste!

### Terminal 1 - FastAPI rodando ✅

```bash
python -m uvicorn app.main:app --reload
```

### Terminal 2 - ngrok rodando ✅

```bash
ngrok http 8000
```

### Terminal 3 - Seu WhatsApp 📱

Envie uma mensagem para o **Twilio Sandbox** (+1 415 523 8886):

```
\> "Oi, tudo bem?"
```

**O que vai acontecer:**

1. ✅ Twilio recebe sua mensagem
2. ✅ Chama seu webhook em `/webhook/whatsapp/twilio`
3. ✅ Seu bot processa
4. ✅ Bot responde algo tipo: "Recebi sua mensagem: 'Oi, tudo bem?' 

Como posso ajudar?"
5. ✅ Você vê a resposta no WhatsApp!

---

## 🔍 Debugging

### Verifique os logs local

No terminal do FastAPI, você verá:

```
📱 [TWILIO] Mensagem de +5561998776092 | SID: SMxxxxxxxx
📝 [TWILIO] Conteúdo: 'Oi, tudo bem?'
✅ [TWILIO] Resposta enviada para +5561998776092
```

---

### Verifique no ngrok

Na janela do ngrok, você vê todas as requisições:

```
POST /webhook/whatsapp/twilio    200 OK     120ms
```

Clique no número da linha pra ver detalhes da request/response.

---

### Verifique no Twilio Console

```
https://www.twilio.com/console/sms/logs
```

Procura por mensagens recentes e vê o status.

---

## ⚠️ Troubleshooting

### ❌ Mensagem não chega

**Causa:** Webhook URL incorreta no Twilio

**Solução:**
1. Confira: `https://abc123.ngrok.io/webhook/whatsapp/twilio`
2. Não esqueça o `/twilio` no final!
3. Salve de novo no Twilio

---

### ❌ "Connection refused"

**Causa:** FastAPI não está rodando ou ngrok desconectou

**Solução:**
1. Inicie FastAPI: `python -m uvicorn app.main:app --reload`
2. Inicie ngrok em outro terminal: `ngrok http 8000`
3. Rode o teste de novo

---

### ❌ "URL changed every time!"

**Realidade:** Sim! ngrok gera nova URL a cada sessão de graça.

**Soluções:**
1. Use plano pago do ngrok (URL fixa)
2. Ou atualiza URL no Twilio cada vez
3. Ou deploy em servidor (melhor solução)

---

### ❌ Bot não responde

**Causa:** Lógica do bot pode estar com erro

**Solução:**
1. Vê os logs do FastAPI
2. Procura por: `❌ Erro processando webhook Twilio`
3. Me manda o erro!

---

## 🎯 Próximos Passos

### 1️⃣ Testar conversa fácil
```
Você: "oi"
Bot: "Recebi sua mensagem: 'oi'. Como posso ajudar?"
```

### 2️⃣ Integrar com OpenAI
```python
# Em _generate_reply():
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": message_body}]
)
return response.choices[0].message.content
```

### 3️⃣ Conectar com seu Use Case

Exemplo - Check-in:
```python
if "check-in" in message_body.lower():
    response_dto = use_case.execute(...)
    return response_dto.message
```

### 4️⃣ Deploy em produção

Quando tudo funcionar localmente, deploy em:
- Heroku
- Railway
- Render
- AWS Lambda

---

## 📞 Teste Rápido

```bash
# 1. Abre 3 terminais

# Terminal 1 - FastAPI
python -m uvicorn app.main:app --reload

# Terminal 2 - ngrok
cd C:\ngrok (ou brew install ngrok)
ngrok http 8000

# Terminal 3 - Teste manual (opcional)
curl -X POST http://localhost:8000/webhook/whatsapp/twilio \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=whatsapp:+5561998776092&Body=Oi&MessageSid=SM123&NumMedia=0"
```

---

## ✅ Checklist Webhook

```
☐ FastAPI rodando em http://localhost:8000
☐ ngrok rodando em outro terminal
☐ URL do ngrok copiada
☐ URL adicionada no Twilio Console
☐ Webhook aponta pra /webhook/whatsapp/twilio
☐ Enviou mensagem no WhatsApp
☐ Recebeu resposta do bot
☐ Viu logs no FastAPI
☐ Viu requisição no ngrok
```

---

**Agora é só interatividade total! 🎉**

Você envia → Bot responde → Funciona bidirecional!

Próximo: Integrar com OpenAI para conversa inteligente 🤖

