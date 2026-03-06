# Quick Start Meta WhatsApp

Passos mínimos para validar Meta no projeto.

## 1) Configure `.env`

```env
META_ACCESS_TOKEN=...
PHONE_NUMBER_ID=...
WEBHOOK_VERIFY_TOKEN=...
OPENAI_API_KEY=...
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=hotel
DATABASE_URL=postgresql://postgres:postgres@db:5432/hotel
REDIS_HOST=redis
REDIS_PORT=6379
NGROK_AUTHTOKEN=...
```

## 2) Suba stack com túnel

```bash
docker compose --profile tunnel up -d --build
```

## 3) Pegue URL pública do ngrok

```bash
curl -s http://localhost:4040/api/tunnels
```

## 4) Configure no Meta

Callback: `https://<ngrok>/webhook/whatsapp`  
Verify token: mesmo valor do `.env`

## 5) Teste

Envie mensagem no WhatsApp e confirme resposta automática.

## Nota de depreciação

Fluxo local manual com `ngrok http 8000` não é o caminho recomendado. O padrão do repositório é `docker compose --profile tunnel up`.
