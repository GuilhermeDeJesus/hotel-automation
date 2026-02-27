# Sumário do Contexto de Hotel

Resumo operacional do recurso de contexto de hotel.

## Estado atual

- Contexto de hotel vem de dados persistidos no banco.
- Contexto é usado no fluxo de conversa via webhook.

## Comandos úteis

```bash
alembic upgrade head
python scripts/seed_hotel.py
python -m uvicorn app.main:app --reload --port 8000
```

## Critério de aceite

Perguntas sobre check-in, políticas e serviços devem refletir dados reais do hotel.
