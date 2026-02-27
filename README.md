# Hotel Automation

Backend para automação de atendimento hoteleiro via WhatsApp com IA, usando FastAPI e arquitetura em camadas.

## O que o projeto faz

- Recebe mensagens de hóspedes via WhatsApp (Meta e Twilio).
- Processa fluxos como check-in, confirmação de reserva e conversa assistida.
- Injeta contexto de hotel e de reserva nas respostas da IA.
- Persiste dados em PostgreSQL e usa Redis para cache.

## Arquitetura (resumo)

- `app/domain`: regras de negócio e contratos.
- `app/application`: casos de uso e serviços.
- `app/infrastructure`: SQL, Redis, OpenAI e clientes WhatsApp.
- `app/interfaces`: API FastAPI e injeção de dependências.

## Endpoints principais

- `GET /webhook/whatsapp` (verificação Meta)
- `POST /webhook/whatsapp` (eventos Meta)
- `POST /webhook/whatsapp/twilio` (eventos Twilio)

## Requisitos

- Python 3.10+
- PostgreSQL
- Redis
- Credenciais OpenAI
- Credenciais de ao menos um provedor WhatsApp (Meta ou Twilio)

## Configuração rápida

1. Instale dependências:

```bash
pip install -r requirements.txt
```

2. Configure `.env` com no mínimo:

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

3. Suba banco e dados base:

```bash
alembic upgrade head
python scripts/seed_hotel.py
```

4. Inicie API:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

## Testes úteis

```bash
python tests/test_conversation_mock.py
python tests/test_openai_simple.py
```

## Documentação

A documentação detalhada está em `docs/`:

- `docs/ARQUITETURA_COMPLETA.md`
- `docs/WHATSAPP_ORQUESTRACAO_GUIA.md`
- `docs/DEPLOYMENT_GUIDE.md`
- `docs/EXAMPLE_FLOW.md`
- `docs/QUICKSTART_META_WHATSAPP.md`
- `docs/QUICKSTART_TWILIO.md`
- `docs/CHECKLIST_PROXIMO_PASSOS.md`

## Observações

- O projeto não possui endpoint de healthcheck dedicado no estado atual.
- O arquivo `app/main.py` ainda contém comentários legados e pode ser simplificado em próximo ciclo.