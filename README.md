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
- `GET /saas/kpis` (KPIs com `source/status`, `granularity=day|week|month`, `series` e `daily_series`)
- `GET /saas/leads` (lista de leads por estágio)
- `GET /saas/funnel` (funil de conversão)
- `GET /saas/timeseries` (série temporal com `granularity=day|week|month`)
- `GET /saas/kpis/compare` (comparação atual vs anterior com séries por granularidade)
- `POST /saas/cache/invalidate` (invalidação manual seletiva de cache analytics, protegido por `X-Admin-Token` e rate-limit)
- `GET /saas/audit-events` (leitura paginada de auditoria admin com filtros e `X-Admin-Token`)
- `GET /saas/audit-events/export` (exportação CSV da auditoria com filtros e `X-Admin-Token`)
- `GET /saas/audit-events/metrics` (métricas agregadas da auditoria com `X-Admin-Token`)
- `POST /saas/audit-events/metrics/snapshot` (gera snapshot diário das métricas de auditoria)
- `GET /saas/audit-events/metrics/history` (consulta histórico diário dos snapshots)
- `GET /saas/audit-events/metrics/status` (status de freshness do último snapshot diário)
- `POST /saas/audit-events/metrics/backfill` (backfill de snapshots por intervalo de datas)
- `GET /saas/audit-events/metrics/gaps` (detecção de dias faltantes no histórico de snapshots)
- `POST /saas/audit-events/metrics/repair` (reparo automático das lacunas de snapshots no intervalo)
	- suporta `dry_run=true` para simular correções sem persistir
- `GET /saas/audit-events/metrics/operations` (histórico paginado das operações auditadas de backfill/repair)
- `GET /saas/audit-events/metrics/operations/export` (exportação CSV das operações auditadas de backfill/repair)
- `GET /saas/audit-events/metrics/operations/metrics` (visão agregada de volume, replay e dry-run das operações auditadas)
- `GET /saas/audit-events/metrics/operations/status` (status operacional com `action_required` e recomendações)
- `GET /saas/audit-events/metrics/operations/status/history` (histórico diário de status operacional com `summary.by_status`)
- `GET /saas/audit-events/metrics/operations/status/history/export` (exportação CSV do histórico diário de status operacional)
- `GET /saas/audit-events/metrics/operations/status/history/compare` (comparação entre período atual e anterior com `delta` de dias sob risco)
- `GET /saas/audit-events/metrics/operations/status/history/compare/export` (exportação CSV da comparação entre período atual e anterior)
- `GET /saas/audit-events/metrics/operations/status/trend` (classificação de tendência `improving|stable|worsening` com `action_required`)
- `GET /saas/audit-events/metrics/operations/status/trend/export` (exportação CSV da tendência operacional)
- `GET /saas/audit-events/metrics/operations/status/trend/status` (severidade da tendência `healthy|warning|critical` com `alert` e `action_required`)
- `GET /saas/audit-events/metrics/operations/status/trend/status/export` (exportação CSV da severidade de tendência operacional)
- `GET /saas/audit-events/metrics/operations/status/trend/overview` (resumo executivo com `priority`, `headline` e `snapshot` de deltas)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/export` (exportação CSV do resumo executivo de tendência)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief` (payload compacto de tendência para monitoramento rápido)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/export` (exportação CSV do payload compacto de tendência)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision` (diretiva operacional rápida `monitor|investigate|escalate`)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/export` (exportação CSV da diretiva operacional rápida)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice` (notificação compacta para alerta com `title` e `message`)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/export` (exportação CSV da notificação compacta de alerta)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch` (payload pronto para envio com `channel` e `dedupe_key`)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/export` (exportação CSV do payload pronto para envio)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes` (roteamento com `targets` e `fallback_targets` por canal)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/export` (exportação CSV do roteamento de dispatch)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief` (resumo compacto de targets com `primary_target` e `fallback_target`)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/export` (exportação CSV do resumo compacto de targets)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision` (decisão rápida de roteamento com `route_decision`)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/export` (exportação CSV da decisão rápida de roteamento)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook` (runbook compacto com checklist operacional)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/export` (exportação CSV do runbook compacto operacional)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment` (atribuição operacional com owner, SLA de ACK e escalonamento)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/export` (exportação CSV da atribuição operacional do runbook)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue` (enfileiramento operacional com prioridade e owner)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/export` (exportação CSV do enfileiramento operacional)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket` (ticket operacional compacto com severidade e estado)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/export` (exportação CSV do ticket operacional compacto)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla` (SLA operacional do ticket com status e risco de violação)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/export` (exportação CSV do SLA operacional do ticket)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch` (monitoramento do SLA com `watch_state` e acionamento de página)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/export` (exportação CSV do monitoramento de SLA)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary` (resumo de monitoramento com modo de escalonamento e follow-up)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/export` (exportação CSV do resumo de monitoramento de SLA)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision` (decisão executiva do monitoramento com ação recomendada)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/export` (exportação CSV da decisão executiva de monitoramento)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch` (despacho executivo com modo e canal de notificação)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/export` (exportação CSV do despacho executivo)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/receipt` (confirmação de despacho com status de entrega)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/receipt/export` (exportação CSV da confirmação de despacho)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/receipt/review` (revisão de confirmação de despacho com estado de análise)
- `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/receipt/review/export` (exportação CSV da revisão de confirmação de despacho)
- Operações de intervalo (`gaps`, `backfill`, `repair`) respeitam limite máximo via `SAAS_AUDIT_SNAPSHOT_MAX_RANGE_DAYS`.
- Operações `backfill` e `repair` suportam processamento em lotes por `batch_size` (default por `SAAS_AUDIT_SNAPSHOT_BATCH_SIZE`).
- Operações `backfill` e `repair` suportam `summary_only` para retornar payload compacto.
- Operações `backfill` e `repair` suportam `request_id` para idempotência (TTL por `SAAS_AUDIT_OPERATION_IDEMPOTENCY_TTL_SECONDS`).
- Operações `backfill` e `repair` também geram auditoria operacional (`event_type=audit_metrics_operation`) com `success|replay|dry_run`.
- Endpoint de métricas das operações inclui alerta por `replay_ratio`, com thresholds em `SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD` e `SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD`.
- Endpoint de status operacional usa `SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES` para orientar frequência de acompanhamento.
- Endpoint de histórico diário de status operacional usa os mesmos thresholds de `replay_ratio` para classificar cada dia.

## Requisitos

- Python 3.10+
- PostgreSQL
- Redis
- Credenciais OpenAI
- Credenciais de ao menos um provedor WhatsApp (Meta ou Twilio)

## Estado atual (Mar/2026)

- Infra padrão: `docker compose` com `app`, `db` (PostgreSQL), `redis` e perfil `tunnel` (`ngrok`).
- Healthcheck ativo em `GET /health`.
- Redis é usado para histórico de conversa e estado de fluxo `flow:<phone>`.
- Redis também é usado para cache de leitura dos endpoints analíticos SaaS (TTL curto), com invalidação seletiva por prefixo `saas:dashboard:*` após novos eventos.
- Invalidação manual de cache analytics disponível em `POST /saas/cache/invalidate` com header `X-Admin-Token`.
- Endpoint de invalidação manual possui rate-limit configurável por `SAAS_CACHE_INVALIDATE_RATE_LIMIT` e `SAAS_CACHE_INVALIDATE_RATE_WINDOW_SECONDS`.
- Endpoint de invalidação manual possui trilha de auditoria em log estruturado (`saas_cache_invalidate_audit`) sem exposição de token.
- Auditoria administrativa também é persistida em PostgreSQL na tabela `saas_admin_audit_events`.
- Eventos persistidos podem ser consultados via `GET /saas/audit-events` com filtros por período e `outcome`.
- Eventos persistidos também podem ser exportados em CSV via `GET /saas/audit-events/export`.
- A auditoria também possui visão agregada em `GET /saas/audit-events/metrics` (outcomes, top IPs e taxa de rate limit), com severidade `healthy|warning|critical` por thresholds (`SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD` e `SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD`).
- O histórico diário dessa severidade é persistido na tabela `saas_audit_metrics_snapshots`, com geração via `POST /saas/audit-events/metrics/snapshot` e leitura via `GET /saas/audit-events/metrics/history`.
- Freshness do último snapshot pode ser monitorado via `GET /saas/audit-events/metrics/status`, usando política configurável por `SAAS_AUDIT_SNAPSHOT_MAX_AGE_DAYS`.
- Busca de reserva por telefone usa normalização numérica (evita mismatch com `+55`, espaços e hífens).
- Fluxo de confirmação (`confirmar reserva`) depende de uma reserva já existente no banco.

## Configuração rápida

1. Instale dependências:

```bash
pip install -r requirements.txt
```

2. Configure `.env` com no mínimo:

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

3. Suba stack e dados base:

```bash
docker compose up -d --build app db redis
docker compose exec -T app alembic upgrade head
docker compose exec -T app python scripts/seed_hotel.py
```

4. Verifique saúde da API:

```bash
curl http://localhost:8000/health
```

## Testes úteis

```bash
docker compose run --rm unit-tests
```

## Testes unitários (Docker)

Com Docker ativo no ambiente, execute os unit tests em container:

```bash
docker compose run --rm unit-tests
```

Para subir stack completa e depois testar:

```bash
docker compose up -d --build
docker compose run --rm unit-tests
```

## Testes de integração com Redis real (Docker)

```bash
docker compose up -d --build
docker compose run --rm integration-tests
```

Esse comando valida:

- persistência de histórico de conversa no Redis real
- persistência de `flow:<phone>` no início de confirmação de reserva
- TTL do estado de fluxo
- limpeza da chave `flow:<phone>` após confirmação

## Testes E2E de negócio (PostgreSQL + Redis reais)

Valida check-in e confirmação de reserva pelo orquestrador principal,
com persistência real em banco e cache:

```bash
docker compose run --rm --build integration-tests python -m pytest tests/integration/test_business_e2e_postgres_redis_real.py -vv
```

## Documentação

A documentação detalhada está em `docs/`:

- `docs/DOCS_STATUS_ATUAL.md`
- `docs/SAAS_MVP_4_FASES.md`
- `docs/ARQUITETURA_COMPLETA.md`
- `docs/WHATSAPP_ORQUESTRACAO_GUIA.md`
- `docs/DEPLOYMENT_GUIDE.md`
- `docs/EXAMPLE_FLOW.md`
- `docs/QUICKSTART_META_WHATSAPP.md`
- `docs/QUICKSTART_TWILIO.md`
- `docs/CHECKLIST_PROXIMO_PASSOS.md`

## Docker (Fase 1)

1. Crie seu `.env` a partir do exemplo:

```bash
cp .env.example .env
```

2. Suba os serviços:

```bash
docker compose up --build
```

3. Verifique API:

```bash
curl http://localhost:8000/health
```

## WhatsApp real (Docker + ngrok)

1. Configure `NGROK_AUTHTOKEN` no `.env`.

2. Suba API, banco, redis e túnel ngrok com um comando:

```bash
docker compose --profile tunnel up -d --build
```

3. Pegue a URL pública do ngrok:

```bash
curl -s http://localhost:4040/api/tunnels
```

4. Configure no Twilio Sandbox (`When a message comes in`):

`https://SEU_DOMINIO_NGROK/webhook/whatsapp/twilio`

5. Acompanhe logs:

```bash
docker compose logs -f app ngrok
```

### Atalho (Makefile)

Comando único para subir stack + túnel e exibir dados do ngrok:

```bash
make whatsapp-test
```

Comandos úteis:

```bash
make logs
make ngrok-url
make unit
make integration
make e2e
make seed-saas
make phase2-1
make snapshot-audit
make snapshot-audit-backfill FROM=2026-03-01 TO=2026-03-03
make snapshot-audit-backfill FROM=2026-03-01 TO=2026-03-03 BATCH_SIZE=2
make snapshot-audit-backfill FROM=2026-03-01 TO=2026-03-03 BATCH_SIZE=2 SUMMARY_ONLY=1
make snapshot-audit-backfill FROM=2026-03-01 TO=2026-03-03 REQUEST_ID=backfill-20260303
make snapshot-audit-gaps FROM=2026-03-01 TO=2026-03-03
make snapshot-audit-repair FROM=2026-03-01 TO=2026-03-03
make snapshot-audit-repair FROM=2026-03-01 TO=2026-03-03 BATCH_SIZE=2
make snapshot-audit-repair-dry-run FROM=2026-03-01 TO=2026-03-03
make down
```

Gerar snapshot para um dia específico:

```bash
make snapshot-audit DATE=2026-03-03
```

## Operações de dados (Redis + Banco)

Limpar cache de conversa no Redis:

```bash
make limpa-cache-redis
```

Limpar apenas reservas (mantendo hotel/quartos):

```bash
docker exec hotel_automation_db psql -U postgres -d hotel -c "TRUNCATE TABLE reservations RESTART IDENTITY CASCADE;"
```

## Observações

- O fluxo de confirmação de reserva funciona sobre reserva já persistida.
- O fluxo de conversa com IA não deve ser interpretado como confirmação transacional automática de reserva.