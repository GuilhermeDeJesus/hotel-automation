# Sumário do Contexto de Hotel

Resumo operacional do recurso de contexto de hotel.

## Estado atual

- Contexto de hotel vem de dados persistidos no banco.
- Contexto é usado no fluxo de conversa via webhook.

## Comandos úteis

```bash
docker compose up -d --build app db redis
docker compose exec -T app alembic upgrade head
docker compose exec -T app python scripts/seed_hotel.py
curl http://localhost:8000/health
```

## Critério de aceite

Perguntas sobre check-in, políticas e serviços devem refletir dados reais do hotel.
