# 🚀 Teste Rápido - Webhook Twilio WhatsApp

## ✅ Status Atual:
- ✅ PostgreSQL rodando
- ✅ Banco 'hotel' criado
- ✅ Tabelas criadas
- ✅ Cliente Twilio configurado
- ✅ Sandbox ativado (+1 415 523 8886)
- ✅ FastAPI rodando (Terminal 1)

---

## 🎯 AGORA: Ativar Webhook

### Terminal 2 - Inicie ngrok:

```bash
python start_ngrok.py
```

**Vai aparecer:**
```
🌐 URL Pública: https://abc123.ngrok.io

🎯 CONFIGURE NO TWILIO AGORA:
   https://abc123.ngrok.io/webhook/whatsapp/twilio
```

**COPIE A URL COMPLETA!**

---

### Navegador - Configure Twilio:

**1. Acesse:**
```
https://www.twilio.com/console/sms/whatsapp/sandbox
```

**2. Desça até "Sandbox Configuration"**

Vai ver algo assim:
```
┌────────────────────────────────────────┐
│ When a message comes in                │
├────────────────────────────────────────┤
│ [____________________________]         │ ← Cole aqui
│                                        │
│ HTTP POST ▼                            │
└────────────────────────────────────────┘
```

**3. Cole a URL DO NGROK** com `/webhook/whatsapp/twilio`:
```
https://abc123.ngrok.io/webhook/whatsapp/twilio
```

**4. Deixe "HTTP POST" selecionado**

**5. Clique em "Save"**

✅ Pronto! Webhook configurado!

---

## 📱 TESTE NO WHATSAPP

### 1. Abra WhatsApp no celular

### 2. Vá para o contato: **+1 415 523 8886**

### 3. Envie a mensagem:
```
Oi
```

### 4. Aguarde 2-5 segundos...

### 5. Vai chegar a resposta:
```
Recebi sua mensagem: 'Oi'

Como posso ajudar?
```

---

## 📊 VERIFICAR LOGS

### Terminal 1 (FastAPI):
```
📱 [TWILIO] Mensagem de +5561998776092 | SID: SMxxxxxxxx
📝 [TWILIO] Conteúdo: 'Oi'
✅ [TWILIO] Resposta enviada para +5561998776092
```

### Terminal 2 (ngrok):
```
POST /webhook/whatsapp/twilio    200 OK
```

---

## 🎉 SE FUNCIONOU:

**Parabéns!** Seu bot está:
- ✅ Recebendo mensagens do WhatsApp
- ✅ Processando via Twilio webhook
- ✅ Respondendo automaticamente
- ✅ Banco de dados funcionando

---

## ⚠️ SE NÃO FUNCIONOU:

### Checklist:
```
☐ Terminal 1 - FastAPI rodando?
☐ Terminal 2 - ngrok rodando?
☐ URL correta no Twilio? (com /webhook/whatsapp/twilio no final)
☐ Clicou em "Save" no Twilio?
☐ Enviou para +1 415 523 8886?
☐ Fez "join codigo" antes?
```

### Erros Comuns:

**❌ "502 Bad Gateway" no Twilio:**
- FastAPI não está rodando
- Solução: Rode `python -m uvicorn app.main:app --reload`

**❌ Bot não responde:**
- Webhook URL está errada
- Solução: Confere URL no Twilio Console

**❌ Erro 63015:**
- Você não fez "join" no sandbox
- Solução: Envia "join seu-codigo" antes

---

## 🚀 Próximos Passos

Depois que funcionar:

### 1. Integrar OpenAI
```python
# Em _generate_reply():
response = openai.ChatCompletion.create(...)
```

### 2. Implementar Check-in Automático
```
Usuário: "quero fazer check-in"
Bot: "Qual seu nome?"
Usuário: "Kelly"
Bot: "Reserva encontrada! Confirmando check-in..."
```

### 3. Pagamento
```
Bot: "Valor total: R$ 300. Link pagamento: https://..."
```

---

## 🎯 Comandos Úteis

```bash
# Reiniciar FastAPI
Ctrl+C no Terminal 1
python -m uvicorn app.main:app --reload

# Reiniciar ngrok
Ctrl+C no Terminal 2
python start_ngrok.py

# Ver logs do banco
psql -U postgres -d hotel
\dt
SELECT * FROM reservations;
\q
```

---

**Agora é só testar! 🎉**

Qualquer erro, me manda os logs! 📊
