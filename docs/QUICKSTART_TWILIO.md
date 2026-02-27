# Quick Start Twilio WhatsApp

Passos curtos para validar webhook Twilio.

## 1) Configure `.env`

```env
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
OPENAI_API_KEY=...
DATABASE_URL=...
REDIS_HOST=localhost
REDIS_PORT=6379
```

## 2) Suba API e túnel

```bash
python -m uvicorn app.main:app --reload --port 8000
ngrok http 8000
```

## 3) Twilio Sandbox

Configure `When a message comes in` para:

`https://<ngrok>/webhook/whatsapp/twilio`

## 4) Teste

No WhatsApp, faça `join <codigo>` e envie mensagem.
