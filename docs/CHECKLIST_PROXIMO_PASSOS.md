# Checklist de Próximos Passos

Lista objetiva para continuar evolução do projeto.

## Documento principal de execução

Para o plano completo de 0% a 100% com casos reais (check-in, confirmação, extensão, check-out e variações de hotel), use:

- `docs/GUIA_100_PERCENT_CASOS_REAIS.md`

## Infra e setup

- [ ] PostgreSQL ativo
- [ ] Redis ativo
- [ ] `.env` completo com segredos válidos
- [ ] `alembic upgrade head`
- [ ] `python scripts/seed_hotel.py`

## Execução

- [ ] `python -m uvicorn app.main:app --reload --port 8000`
- [ ] Meta webhook validado (`GET/POST /webhook/whatsapp`)
- [ ] Twilio webhook validado (`POST /webhook/whatsapp/twilio`)

## Qualidade

- [ ] Rodar testes em `tests/unit`
- [ ] Criar/fortalecer testes de integração de webhook

## Evolução técnica

1. Adicionar endpoint de healthcheck.
2. Melhorar monitoramento e alertas.
3. Revisar docker-compose para execução padronizada.
