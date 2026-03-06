# Guia de Deploy (Atual)

Guia operacional alinhado com o estado atual do repositório (Mar/2026).

## Requisitos

- Docker + Docker Compose
- Credenciais OpenAI
- Credenciais Meta e/ou Twilio

## Variáveis mínimas (`.env`)

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=hotel
DATABASE_URL=postgresql://postgres:postgres@db:5432/hotel
OPENAI_API_KEY=...

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_USERNAME=
REDIS_PASSWORD=

META_ACCESS_TOKEN=...
PHONE_NUMBER_ID=...
WEBHOOK_VERIFY_TOKEN=...

TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

NGROK_AUTHTOKEN=...
```

## Passos

```bash
cp .env.example .env
docker compose up -d --build app db redis
docker compose exec -T app alembic upgrade head
docker compose exec -T app python scripts/seed_hotel.py
curl http://localhost:8000/health
```

## WhatsApp em ambiente real de teste (Twilio + ngrok)

```bash
docker compose --profile tunnel up -d --build
curl -s http://localhost:4040/api/tunnels
```

Configure no Twilio Sandbox (`When a message comes in`):

`https://SEU_DOMINIO_NGROK/webhook/whatsapp/twilio`

## Endpoints de produção

- `GET /webhook/whatsapp`
- `POST /webhook/whatsapp`
- `POST /webhook/whatsapp/twilio`

## Checklist pós-deploy

1. Validar webhook Meta.
2. Validar webhook Twilio.
3. Confirmar recebimento e resposta no WhatsApp.
4. Confirmar geração de logs (`docker compose logs -f app ngrok`).
5. Validar acesso a Redis e PostgreSQL pelos containers.

## Nota de depreciação

Comandos de `uvicorn` + `ngrok http 8000` local continuam possíveis, mas o fluxo recomendado do projeto é Docker-first para evitar drift de ambiente.
