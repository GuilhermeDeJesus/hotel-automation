# Guia de Deploy (Atual)

Guia alinhado com o estado atual do repositório.

## Requisitos

- Python 3.10+
- PostgreSQL
- Redis
- Credenciais OpenAI
- Credenciais Meta e/ou Twilio

## Variáveis mínimas (`.env`)

```env
DATABASE_URL=postgresql://postgres:senha@localhost:5432/hotel
OPENAI_API_KEY=...

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

META_ACCESS_TOKEN=...
PHONE_NUMBER_ID=...
WEBHOOK_VERIFY_TOKEN=...

TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

## Passos

```bash
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_hotel.py
python -m uvicorn app.main:app --reload --port 8000
```

## Endpoints de produção

- `GET /webhook/whatsapp`
- `POST /webhook/whatsapp`
- `POST /webhook/whatsapp/twilio`

## Checklist pós-deploy

1. Validar webhook Meta.
2. Validar webhook Twilio.
3. Confirmar recebimento e resposta no WhatsApp.
4. Confirmar geração de logs.
