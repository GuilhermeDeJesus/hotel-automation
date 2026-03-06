# Quick Start Twilio WhatsApp

Passos curtos para validar webhook Twilio.

## 1) Configure `.env`

```env
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
OPENAI_API_KEY=...
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=hotel
DATABASE_URL=postgresql://postgres:postgres@db:5432/hotel
REDIS_HOST=redis
REDIS_PORT=6379
NGROK_AUTHTOKEN=...
```

## 2) Suba API e túnel

```bash
docker compose --profile tunnel up -d --build
curl -s http://localhost:4040/api/tunnels
```

## 3) Twilio Sandbox

Configure `When a message comes in` para:

`https://<ngrok>/webhook/whatsapp/twilio`

## 4) Teste

No WhatsApp, faça `join <codigo>` e envie mensagem.

## 5) Logs

```bash
docker compose logs -f app ngrok
```

## Nota de depreciação

Fluxo manual `uvicorn` + `ngrok http 8000` foi substituído por execução via Docker Compose (`--profile tunnel`) como padrão do projeto.
