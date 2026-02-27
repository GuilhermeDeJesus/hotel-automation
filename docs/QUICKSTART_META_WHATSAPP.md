# Quick Start Meta WhatsApp

Passos mínimos para validar Meta no projeto.

## 1) Configure `.env`

```env
META_ACCESS_TOKEN=...
PHONE_NUMBER_ID=...
WEBHOOK_VERIFY_TOKEN=...
OPENAI_API_KEY=...
DATABASE_URL=...
REDIS_HOST=localhost
REDIS_PORT=6379
```

## 2) Suba a API

```bash
python -m uvicorn app.main:app --reload --port 8000
```

## 3) Exponha com ngrok

```bash
ngrok http 8000
```

## 4) Configure no Meta

Callback: `https://<ngrok>/webhook/whatsapp`  
Verify token: mesmo valor do `.env`

## 5) Teste

Envie mensagem no WhatsApp e confirme resposta automática.
