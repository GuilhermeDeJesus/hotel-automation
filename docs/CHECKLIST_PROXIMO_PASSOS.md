# Checklist de Próximos Passos

Lista objetiva para continuar evolução do projeto.

## Documento principal de execução

Para o plano completo de 0% a 100% com casos reais (check-in, confirmação, extensão, check-out e variações de hotel), use:

- `docs/GUIA_100_PERCENT_CASOS_REAIS.md`

## Infra e setup

- [x] PostgreSQL ativo (`docker compose`)
- [x] Redis ativo (`docker compose`)
- [ ] `.env` completo com segredos válidos e rotacionados
- [x] Migrações (`alembic upgrade head`)
- [x] Seed de hotel + quartos (`python scripts/seed_hotel.py`)

## Execução

- [x] `docker compose up -d --build app db redis`
- [x] Healthcheck ativo (`GET /health`)
- [ ] Meta webhook validado (`GET/POST /webhook/whatsapp`)
- [ ] Twilio webhook validado (`POST /webhook/whatsapp/twilio`)

## Qualidade

- [x] Rodar testes em `tests/unit`
- [x] Rodar integração com Redis real
- [x] Rodar E2E de negócio com PostgreSQL + Redis reais
- [ ] Criar/fortalecer testes de integração de webhook externo (Meta/Twilio sandbox)

## Evolução técnica

1. Reforçar observabilidade (logs estruturados + alertas).
2. Consolidar estratégia de criação transacional de reserva a partir de conversa.
3. Expandir cobertura de testes de webhook com provedores externos.
