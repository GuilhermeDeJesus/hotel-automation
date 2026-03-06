# SaaS MVP - Roadmap em 4 Fases

Este documento define o plano oficial para evoluir o `hotel-automation` em um SaaS para hotelaria.

Objetivo: transformar o backend atual (WhatsApp + IA + fluxos transacionais) em produto com painel de resultados para negócio.

---

## Fase 1 — Fundação de Ambiente e Operação (Infra MVP)

**Status:** Concluída

### Objetivos

- Padronizar ambiente de desenvolvimento e deploy com Docker.
- Garantir previsibilidade de execução local, staging e VPS.
- Manter endpoint de healthcheck para observabilidade básica.

### Entregáveis

1. `docker-compose.yml` com:
   - `app` (FastAPI)
   - `db` (PostgreSQL)
   - `redis`
   - volumes persistentes
   - healthchecks
2. `dockerfile` corrigido para execução da aplicação.
3. Endpoint `GET /health`.
4. `.env.example` com variáveis mínimas.

### Critérios de aceite

- `docker compose up --build` sobe `app`, `db` e `redis` com healthchecks.
- API responde `200` em `/health`.
- App consegue conectar no PostgreSQL e Redis via variáveis de ambiente.
- Execução com túnel `ngrok` disponível via profile `tunnel`.

---

## Fase 2 — Camada SaaS de Métricas e Leads (Backend)

**Status:** Em andamento

### Objetivos

- Criar visão analítica do atendimento para gestores de hotel.
- Medir geração de leads e evolução no funil de conversão.

### Escopo funcional

- Captura de eventos de conversa e eventos transacionais.
- Entidade de lead com estágio do funil.
- APIs de leitura para dashboard.

### Endpoints MVP (propostos)

- `GET /saas/kpis?from=...&to=...`
- `GET /saas/leads?from=...&to=...&status=...`
- `GET /saas/funnel?from=...&to=...`

### Progresso atual

- Modelagem SQL criada para leads e eventos analíticos (`saas_leads`, `saas_analytics_events`).
- Migração Alembic adicionada para estrutura da Fase 2.
- Endpoints `/saas/kpis`, `/saas/leads`, `/saas/funnel` implementados e respondendo.
- Captura de eventos de entrada/saída integrada ao webhook (Meta/Twilio).

### Fase 2.1 (implementada)

- Seed operacional de analytics/leads para popular dashboard: `scripts/seed_saas_metrics.py`.
- Testes de integração de API SaaS: `tests/integration/test_saas_dashboard_endpoints.py`.
- Atalhos de execução:
   - `make seed-saas`
   - `make phase2-1`

### Fase 2.2 (implementada)

- KPIs com filtros adicionais:
   - `GET /saas/kpis?from=YYYY-MM-DD&to=YYYY-MM-DD&source=twilio|meta&status=STAGE`
- Série temporal diária incluída na resposta de KPIs (`daily_series`).
- Janela padrão automática de 7 dias quando `from/to` não são informados.
- Testes de integração cobrindo filtros e estrutura de série temporal.

### Fase 2.3 (implementada)

- Endpoint dedicado de série temporal:
   - `GET /saas/timeseries?from=YYYY-MM-DD&to=YYYY-MM-DD&source=...&status=...`
- Endpoint de comparação entre período atual vs período anterior equivalente:
   - `GET /saas/kpis/compare?from=YYYY-MM-DD&to=YYYY-MM-DD&source=...&status=...`
- Resposta de comparação com blocos `current`, `previous` e `delta` (absoluto e percentual).
- Cobertura de testes de integração para os novos contratos de API.

### Fase 2.4 (implementada)

- Agregação temporal por granularidade em analytics:
   - `granularity=day|week|month`
- Aplicado nos endpoints:
   - `GET /saas/timeseries`
   - `GET /saas/kpis/compare`
- `kpis/compare` agora inclui séries agregadas do período atual e anterior:
   - `series_current`
   - `series_previous`
- Cobertura de integração ampliada para validação de granularidade semanal e mensal.

### Fase 2.5 (implementada)

- `GET /saas/kpis` agora também suporta granularidade:
   - `granularity=day|week|month`
- Resposta de KPIs agora inclui:
   - `series` (série agregada pela granularidade solicitada)
   - `granularity` no payload e em `period`
- Compatibilidade preservada com `daily_series` (série diária legada).

### Fase 2.6 (implementada)

- Cache de leitura para endpoints analíticos no `GetSaaSDashboardUseCase` usando Redis.
- Chave de cache determinística por operação + parâmetros (`from`, `to`, `source`, `status`, `granularity`).
- TTL curto para reduzir custo de agregações mantendo atualização frequente (120s).
- Cache aplicado em:
   - KPIs
   - Leads
   - Funnel
   - Timeseries
   - KPI comparison

### Fase 2.7 (implementada)

- Invalidação seletiva de cache analítico após novos eventos de tracking no webhook.
- Escopo da invalidação restrito ao prefixo `saas:dashboard:*`.
- Chaves não relacionadas (ex.: histórico de conversa/fluxo) permanecem preservadas.
- Implementação centralizada no caso de uso (`invalidate_analytics_cache`) com chamada após persistência bem-sucedida.

### Fase 2.8 (implementada)

- Endpoint manual para invalidação seletiva do cache analítico:
   - `POST /saas/cache/invalidate`
- Remove apenas chaves do prefixo `saas:dashboard:*`.
- Mantém chaves operacionais não analíticas intactas (ex.: `flow:<phone>`).
- Cobertura de integração adicionada para validar contrato e efeito da limpeza seletiva.

### Fase 2.9 (implementada)

- Proteção do endpoint manual de invalidação com token administrativo.
- Header obrigatório:
   - `X-Admin-Token`
- Token configurado por variável de ambiente:
   - `SAAS_ADMIN_TOKEN`
- Contratos de erro adicionados:
   - `503` quando token não está configurado
   - `401` quando header está ausente
   - `403` quando token é inválido
- Cobertura de integração para cenários de autorização e sucesso.

### Fase 2.10 (implementada)

- Rate-limit no endpoint administrativo `POST /saas/cache/invalidate`.
- Controle por IP do cliente, com janela deslizante simples em Redis.
- Parâmetros configuráveis via ambiente:
   - `SAAS_CACHE_INVALIDATE_RATE_LIMIT`
   - `SAAS_CACHE_INVALIDATE_RATE_WINDOW_SECONDS`
- Contrato de erro adicional:
   - `429` quando limite de requisições é excedido (`Retry-After` no header).
- Cobertura de integração adicionada para o cenário de estouro de limite.

### Fase 2.11 (implementada)

- Auditoria operacional do endpoint administrativo `POST /saas/cache/invalidate`.
- Emissão de evento de log estruturado `saas_cache_invalidate_audit` para todas as tentativas.
- Campos auditados:
   - `client_ip`
   - `outcome` (`success`, `rejected`, `rate_limited`)
   - `deleted_keys` (quando sucesso)
   - `retry_after` (quando rate limited)
   - `reason` (motivo de rejeição/limite)
- Sem exposição de segredo (`X-Admin-Token` não é logado).
- Cobertura de integração para validação de emissão da trilha de auditoria.

### Fase 2.12 (implementada)

- Persistência da trilha de auditoria administrativa em PostgreSQL.
- Nova tabela:
   - `saas_admin_audit_events`
- Cada tentativa de `POST /saas/cache/invalidate` agora grava auditoria em banco e também em log.
- Campos persistidos:
   - `event_type`
   - `client_ip`
   - `outcome`
   - `deleted_keys`
   - `retry_after`
   - `reason`
   - `created_at`
- Migração Alembic adicionada para criação da estrutura e índices.
- Cobertura de integração adicionada para validar gravação efetiva do evento na tabela.

### Fase 2.13 (implementada)

- Endpoint de leitura da auditoria persistida:
   - `GET /saas/audit-events`
- Protegido por `X-Admin-Token` (mesma política admin da invalidação).
- Filtros suportados:
   - `from`
   - `to`
   - `outcome`
- Paginação suportada:
   - `page`
   - `page_size` (limite máximo 100)
- Contrato de resposta inclui:
   - `items`
   - `pagination`
   - `filters`
- Cobertura de integração para paginação + filtro por `outcome` e período.

### Fase 2.14 (implementada)

- Endpoint de exportação CSV da auditoria:
   - `GET /saas/audit-events/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados no export:
   - `from`
   - `to`
   - `outcome`
- Formato de saída:
   - `text/csv`
   - Header `Content-Disposition` para download (`saas_audit_events.csv`)
- Cobertura de integração para validação de conteúdo CSV e aplicação de filtros.

### Fase 2.15 (implementada)

- Endpoint de métricas agregadas da auditoria:
   - `GET /saas/audit-events/metrics`
- Protegido por `X-Admin-Token`.
- Filtro por período:
   - `from`
   - `to`
- Métricas retornadas:
   - `total_attempts`
   - `by_outcome` (contagem por resultado)
   - `rate_limited.count` e `rate_limited.ratio`
   - `top_ips` (top 5 IPs com tentativas e eventos de rate limit)
   - `period`
- Cobertura de integração adicionada para validar agregações principais do endpoint.

### Fase 2.16 (implementada)

- Camada de alerta no endpoint `GET /saas/audit-events/metrics`.
- Alerta baseado no indicador `rate_limited.ratio`.
- Threshold configurável via ambiente:
   - `SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD`
- Resposta agora inclui bloco:
   - `alert.metric`
   - `alert.current`
   - `alert.warning_threshold`
   - `alert.status` (`healthy` | `warning`)
- Cobertura de integração adicionada para cenário em que a razão excede o limite e gera `warning`.

### Fase 2.17 (implementada)

- Evolução da severidade de alerta para 3 níveis no endpoint `GET /saas/audit-events/metrics`:
   - `healthy`
   - `warning`
   - `critical`
- Threshold crítico configurável via ambiente:
   - `SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD`
- Regra de avaliação:
   - `critical` quando `rate_limited.ratio` > `critical_threshold`
   - `warning` quando `rate_limited.ratio` > `warning_threshold`
   - `healthy` caso contrário
- Bloco `alert` agora inclui também:
   - `alert.critical_threshold`
- Cobertura de integração adicionada para cenários `warning` e `critical`.

### Fase 2.18 (implementada)

- Histórico diário de severidade das métricas de auditoria com persistência em tabela dedicada:
   - `saas_audit_metrics_snapshots`
- Endpoint para gerar snapshot sob demanda:
   - `POST /saas/audit-events/metrics/snapshot`
- Endpoint para consultar histórico de snapshots:
   - `GET /saas/audit-events/metrics/history`
- Ambos protegidos por `X-Admin-Token`.
- Snapshot armazena:
   - `snapshot_date`
   - `total_attempts`
   - `rate_limited_count`
   - `rate_limited_ratio`
   - `alert_status`
   - thresholds aplicados e agregações (`by_outcome`, `top_ips`)
- Migração Alembic adicionada para criação da estrutura.
- Cobertura de integração adicionada para criação e leitura do histórico.

### Fase 2.19 (implementada)

- Job agendável para geração automática de snapshot diário de risco.
- Script operacional adicionado:
   - `scripts/generate_audit_metrics_snapshot.py`
- Entrada opcional por argumento:
   - `--date`
   - `--from`
   - `--to`
- Avaliação de severidade no job com os mesmos thresholds da API:
   - `SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD`
   - `SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD`
- Snapshot é persistido por upsert para a data alvo (idempotência por dia).
- Atalho de execução adicionado no Makefile:
   - `make snapshot-audit`
   - `make snapshot-audit DATE=YYYY-MM-DD`

### Fase 2.20 (implementada)

- Endpoint operacional para monitorar freshness do último snapshot diário:
   - `GET /saas/audit-events/metrics/status`
- Endpoint protegido por `X-Admin-Token`.
- Retorna status operacional:
   - `missing` quando ainda não há snapshot persistido
   - `fresh` quando último snapshot está dentro da política de idade
   - `stale` quando último snapshot está vencido
- Política de validade configurável via ambiente:
   - `SAAS_AUDIT_SNAPSHOT_MAX_AGE_DAYS` (default: `1`)
- Payload inclui:
   - metadados de freshness (`age_days`, `max_age_days`, `is_fresh`)
   - `latest_snapshot` com o último registro persistido

### Fase 2.21 (implementada)

- Backfill operacional de snapshots diários para recuperar histórico faltante.
- Endpoint administrativo adicionado:
   - `POST /saas/audit-events/metrics/backfill?from=YYYY-MM-DD&to=YYYY-MM-DD`
- Endpoint protegido por `X-Admin-Token`.
- Para cada dia no intervalo, o sistema:
   - calcula métricas do dia
   - avalia severidade (`healthy|warning|critical`)
   - persiste snapshot por upsert (idempotência)
- Script operacional também suporta backfill:
   - `python scripts/generate_audit_metrics_snapshot.py --backfill-from YYYY-MM-DD --backfill-to YYYY-MM-DD`
- Atalho Makefile para operação:
   - `make snapshot-audit-backfill FROM=YYYY-MM-DD TO=YYYY-MM-DD`

### Fase 2.22 (implementada)

- Detecção operacional de lacunas no histórico de snapshots diários.
- Endpoint administrativo adicionado:
   - `GET /saas/audit-events/metrics/gaps?from=YYYY-MM-DD&to=YYYY-MM-DD`
- Endpoint protegido por `X-Admin-Token`.
- Resposta inclui:
   - `total_days`
   - `present_days`
   - `missing_count`
   - `missing_dates`
- Script operacional com modo de detecção:
   - `python scripts/generate_audit_metrics_snapshot.py --gaps-from YYYY-MM-DD --gaps-to YYYY-MM-DD`
- Atalho Makefile para diagnóstico rápido:
   - `make snapshot-audit-gaps FROM=YYYY-MM-DD TO=YYYY-MM-DD`

### Fase 2.23 (implementada)

- Auto-repair operacional das lacunas de snapshots diários.
- Endpoint administrativo adicionado:
   - `POST /saas/audit-events/metrics/repair?from=YYYY-MM-DD&to=YYYY-MM-DD`
- Endpoint protegido por `X-Admin-Token`.
- Fluxo da operação:
   - identifica dias faltantes no intervalo
   - gera snapshots apenas para os dias ausentes
   - preserva dias já preenchidos
- Resposta inclui:
   - `missing_before`
   - `created`
   - `created_dates`
   - `missing_after`
- Script operacional com modo de reparo:
   - `python scripts/generate_audit_metrics_snapshot.py --repair-from YYYY-MM-DD --repair-to YYYY-MM-DD`
- Atalho Makefile:
   - `make snapshot-audit-repair FROM=YYYY-MM-DD TO=YYYY-MM-DD`

### Fase 2.24 (implementada)

- Modo de simulação segura (`dry_run`) para operação de repair.
- Endpoint `POST /saas/audit-events/metrics/repair` agora suporta:
   - `dry_run=true`
- Em `dry_run`, o sistema:
   - identifica dias faltantes
   - retorna plano de correção
   - não grava snapshots no banco
- Resposta em modo simulação inclui:
   - `planned`
   - `planned_dates`
   - `created=0`
- Script operacional também suporta simulação:
   - `python scripts/generate_audit_metrics_snapshot.py --repair-from YYYY-MM-DD --repair-to YYYY-MM-DD --repair-dry-run`
- Atalho Makefile:
   - `make snapshot-audit-repair-dry-run FROM=YYYY-MM-DD TO=YYYY-MM-DD`

### Fase 2.25 (implementada)

- Guardrail operacional para limitar o tamanho de janelas de data em operações de range.
- Variável de ambiente adicionada:
   - `SAAS_AUDIT_SNAPSHOT_MAX_RANGE_DAYS` (default: `90`)
- Aplicado nos endpoints:
   - `GET /saas/audit-events/metrics/gaps`
   - `POST /saas/audit-events/metrics/backfill`
   - `POST /saas/audit-events/metrics/repair`
- Aplicado também no script operacional para modos:
   - `--gaps-from/--gaps-to`
   - `--backfill-from/--backfill-to`
   - `--repair-from/--repair-to`
- Quando excedido, a operação retorna erro explícito de faixa acima do máximo permitido.

### Fase 2.26 (implementada)

- Processamento em lotes (`batch_size`) para operações pesadas de snapshots.
- Aplicado nos endpoints:
   - `POST /saas/audit-events/metrics/backfill`
   - `POST /saas/audit-events/metrics/repair`
- Parâmetro opcional:
   - `batch_size` (1..200)
- Default configurável via ambiente:
   - `SAAS_AUDIT_SNAPSHOT_BATCH_SIZE` (default `30`)
- Resposta operacional agora inclui resumo por lote:
   - `batch_size`
   - `batches[]` com faixa (`from/to`) e quantidade processada.
- Script operacional também suporta `--batch-size` para modos `backfill` e `repair`.

### Fase 2.27 (implementada)

- Modo de resposta compacta para operações pesadas (`summary_only`).
- Aplicado nos endpoints:
   - `POST /saas/audit-events/metrics/backfill`
   - `POST /saas/audit-events/metrics/repair`
- Parâmetro opcional:
   - `summary_only=true`
- Em modo compacto:
   - remove listas pesadas (`items` / `created_dates`)
   - mantém resumo com `created`, `batch_size`, `batches` e contadores de itens omitidos.
- Script operacional também suporta:
   - `--summary-only`

### Fase 2.28 (implementada)

- Idempotência explícita para operações administrativas pesadas.
- Aplicado nos endpoints:
   - `POST /saas/audit-events/metrics/backfill`
   - `POST /saas/audit-events/metrics/repair`
- Novo parâmetro opcional:
   - `request_id`
- Quando o mesmo `request_id` é reenviado com os mesmos parâmetros:
   - a resposta é retornada do cache idempotente
   - o payload sinaliza `idempotent_replay=true`
   - evita reprocessamento acidental
- TTL da janela de idempotência configurável:
   - `SAAS_AUDIT_OPERATION_IDEMPOTENCY_TTL_SECONDS` (default `86400`)
- Script operacional também suporta:
   - `--request-id`

### Fase 2.29 (implementada)

- Auditoria operacional de `backfill/repair` persistida na trilha administrativa.
- Cada execução agora emite evento `audit_metrics_operation` com:
   - `outcome` (`success`, `replay`, `dry_run`)
   - contagem processada
   - resumo do contexto operacional (`request_id`, faixa, batch, flags)
- Em replays idempotentes (`request_id` repetido), o sistema:
   - retorna payload em replay
   - registra auditoria com `outcome=replay`
- Sem necessidade de nova migração (reuso da tabela `saas_admin_audit_events`).

### Fase 2.30 (implementada)

- Endpoint dedicado para consultar operações auditadas de snapshots.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `outcome`
   - `operation` (`backfill` ou `repair`)
   - `request_id`
- Paginação suportada:
   - `page`
   - `page_size`
- Retorna visão operacional já normalizada:
   - `operation`
   - `request_id`
   - `processed_count`
   - `outcome`
   - `created_at`

### Fase 2.31 (implementada)

- Exportação CSV das operações auditadas de snapshot.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados no export:
   - `from`
   - `to`
   - `outcome`
   - `operation`
   - `request_id`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations.csv`)

### Fase 2.32 (implementada)

- Visão agregada das operações auditadas de snapshot.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/metrics`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
   - `request_id`
- Métricas retornadas:
   - `total_operations`
   - `by_outcome`
   - `by_operation`
   - `success_count`, `replay_count`, `dry_run_count`
   - `replay_ratio`
   - `total_processed`
   - `unique_request_ids`

### Fase 2.33 (implementada)

- Camada de alerta para `GET /saas/audit-events/metrics/operations/metrics`.
- Alerta baseado em `replay_ratio` das operações auditadas.
- Thresholds configuráveis via ambiente:
   - `SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD` (default `0.15`)
   - `SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD` (default `0.35`)
- Resposta agora inclui bloco:
   - `alert.metric` (`operations_replay_ratio`)
   - `alert.current`
   - `alert.warning_threshold`
   - `alert.critical_threshold`
   - `alert.status` (`healthy|warning|critical`)

### Fase 2.34 (implementada)

- Endpoint de status operacional para operações auditadas com recomendação de ação.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status`
- Protegido por `X-Admin-Token`.
- Retorna:
   - `status` (`healthy|warning|critical`)
   - `action_required` (boolean)
   - `alert`
   - resumo de métricas (`total_operations`, `replay_count`, `replay_ratio`, etc.)
   - `recommendations` para resposta operacional
   - `next_check_in_minutes` configurável por `SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES`

### Fase 2.35 (implementada)

- Histórico diário de status operacional das operações auditadas.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/history`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna:
   - `items[]` com status diário (`healthy|warning|critical`)
   - `action_required` por dia
   - `alert` diário com thresholds aplicados
   - `summary` agregado (`days`, `by_status`, `action_required_days`)

### Fase 2.36 (implementada)

- Exportação CSV do histórico diário de status operacional das operações auditadas.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/history/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_history.csv`)

### Fase 2.37 (implementada)

- Comparação de tendência do status operacional entre período atual e período anterior equivalente.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/history/compare`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna:
   - `current_period.summary`
   - `previous_period.summary`
   - `delta` com variação de `action_required_days`, `warning_days` e `critical_days`

### Fase 2.38 (implementada)

- Exportação CSV da comparação de tendência de status operacional entre períodos.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/history/compare/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_history_compare.csv`)

### Fase 2.39 (implementada)

- Endpoint de tendência operacional entre períodos para resposta proativa.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna:
   - `trend` (`improving|stable|worsening`)
   - `action_required`
   - `recommendations`
   - payload completo de comparação (`current_period`, `previous_period`, `delta`)

### Fase 2.40 (implementada)

- Exportação CSV da tendência operacional para integração com planilhas/BI.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend.csv`)

### Fase 2.41 (implementada)

- Status de severidade da tendência operacional para decisão imediata.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/status`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna:
   - `status` (`healthy|warning|critical`)
   - `alert` com deltas e dias de risco atuais
   - `action_required`
   - `trend` + `recommendations`
   - payload completo de comparação (`current_period`, `previous_period`, `delta`)

### Fase 2.42 (implementada)

- Exportação CSV do status de tendência operacional.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/status/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_status.csv`)

### Fase 2.43 (implementada)

- Overview executivo de tendência operacional para acompanhamento rápido.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna:
   - `status` (`healthy|warning|critical`)
   - `trend` (`improving|stable|worsening`)
   - `priority` (`low|medium|high`)
   - `headline` executivo
   - `action_required`
   - `snapshot` com deltas e dias de risco
   - `next_check_in_minutes`

### Fase 2.44 (implementada)

- Exportação CSV do overview executivo de tendência operacional.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview.csv`)

### Fase 2.45 (implementada)

- Endpoint compacto para leitura rápida do risco operacional de tendência.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload enxuto com:
   - `status`, `trend`, `priority`, `headline`
   - `action_required`
   - `period` atual
   - `snapshot` de deltas principais
   - `next_check_in_minutes`

### Fase 2.46 (implementada)

- Exportação CSV do payload compacto de tendência operacional.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief.csv`)

### Fase 2.47 (implementada)

- Endpoint de decisão operacional rápida para o payload compacto de tendência.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload enxuto com:
   - `status`, `trend`, `priority`
   - `decision` (`monitor|investigate|escalate`) e `reason`
   - `action_required`
   - `period` atual
   - `snapshot` de deltas principais
   - `next_check_in_minutes`

### Fase 2.48 (implementada)

- Exportação CSV da diretiva operacional rápida do payload compacto de tendência.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision.csv`)

### Fase 2.49 (implementada)

- Endpoint de notificação compacta para consumo por canais de alerta operacional.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload compacto com:
   - `status`, `trend`, `priority`, `decision`
   - `title` e `message` prontos para notificação
   - `action_required`
   - `period` atual
   - `next_check_in_minutes`

### Fase 2.50 (implementada)

- Exportação CSV da notificação compacta de alerta operacional.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision_notice.csv`)

### Fase 2.51 (implementada)

- Endpoint de payload pronto para envio de notificação operacional.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload compacto com:
   - `channel` de despacho (`incident|ops-alert|ops-monitor`)
   - `dedupe_key` para idempotência no canal de alerta
   - `title`, `message`, `status`, `trend`, `priority`, `decision`
   - `action_required`, `period`, `next_check_in_minutes`

### Fase 2.52 (implementada)

- Exportação CSV do payload pronto para envio de notificação operacional.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch.csv`)

### Fase 2.53 (implementada)

- Endpoint de roteamento de dispatch para escolher destinos por canal com fallback.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload compacto com:
   - `channel`, `targets`, `fallback_channel`, `fallback_targets`
   - `dedupe_key` para idempotência de envio
   - `status`, `trend`, `priority`, `action_required`
   - `operation`, `period`, `next_check_in_minutes`

### Fase 2.54 (implementada)

- Exportação CSV do roteamento de dispatch para integração com operação externa.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes.csv`)

### Fase 2.55 (implementada)

- Endpoint de resumo compacto do roteamento de dispatch para consumo rápido.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload compacto com:
   - `channel`, `primary_target`, `fallback_target`
   - `targets_count`, `fallback_targets_count`
   - `status`, `trend`, `priority`, `action_required`
   - `operation`, `period`, `next_check_in_minutes`

### Fase 2.56 (implementada)

- Exportação CSV do resumo compacto de roteamento de dispatch.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief.csv`)

### Fase 2.57 (implementada)

- Endpoint de decisão rápida de roteamento para operação em tempo real.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload compacto com:
   - `route_decision` (`escalate_immediately|dispatch_primary|monitor_only`)
   - `channel`, `primary_target`, `fallback_target`
   - `status`, `trend`, `priority`, `action_required`
   - `operation`, `period`, `next_check_in_minutes`

### Fase 2.58 (implementada)

- Exportação CSV da decisão rápida de roteamento operacional.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision.csv`)

### Fase 2.59 (implementada)

- Endpoint de runbook operacional compacto para ação imediata após decisão de roteamento.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload compacto com:
   - `route_decision`, `channel`, `primary_target`
   - `status`, `trend`, `priority`, `action_required`
   - `checklist` de ações recomendadas
   - `operation`, `period`, `next_check_in_minutes`

### Fase 2.60 (implementada)

- Exportação CSV do runbook operacional compacto.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook.csv`)

### Fase 2.61 (implementada)

- Endpoint JSON de atribuição operacional para execução do runbook.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload compacto com:
   - `owner`, `escalation_target`
   - `ack_required`, `ack_deadline_minutes`
   - `route_decision`, `channel`, `primary_target`
   - `status`, `trend`, `priority`, `checklist_size`
   - `operation`, `period`, `next_check_in_minutes`

### Fase 2.62 (implementada)

- Exportação CSV da atribuição operacional do runbook.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment.csv`)

### Fase 2.63 (implementada)

- Endpoint JSON de enfileiramento operacional após atribuição do runbook.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload compacto com:
   - `queue_name`, `queue_priority`
   - `owner`, `escalation_target`
   - `ack_required`, `ack_deadline_minutes`
   - `route_decision`, `channel`, `primary_target`
   - `status`, `trend`, `priority`
   - `operation`, `period`, `next_check_in_minutes`

### Fase 2.64 (implementada)

- Exportação CSV do enfileiramento operacional.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue.csv`)

### Fase 2.65 (implementada)

- Endpoint JSON de ticket operacional compacto após enfileiramento.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload compacto com:
   - `ticket_type`, `ticket_state`, `ticket_severity`
   - `queue_name`, `queue_priority`
   - `owner`, `escalation_target`
   - `ack_required`, `ack_deadline_minutes`
   - `route_decision`, `channel`, `primary_target`
   - `status`, `trend`, `priority`
   - `operation`, `period`, `next_check_in_minutes`

### Fase 2.66 (implementada)

- Exportação CSV do ticket operacional compacto.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket.csv`)

### Fase 2.67 (implementada)

- Endpoint JSON de SLA operacional do ticket.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload compacto com:
   - `ticket_type`, `ticket_state`, `ticket_severity`
   - `queue_name`, `queue_priority`
   - `ack_required`, `ack_deadline_minutes`
   - `sla_status`, `breach_risk`
   - `status`, `trend`, `priority`
   - `operation`, `period`, `next_check_in_minutes`

### Fase 2.68 (implementada)

- Exportação CSV do SLA operacional do ticket.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla.csv`)

### Fase 2.69 (implementada)

- Endpoint JSON de monitoramento do SLA operacional do ticket.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload compacto com:
   - `watch_state`, `should_page`
   - `sla_status`, `breach_risk`
   - `ticket_type`, `ticket_state`, `ticket_severity`
   - `queue_name`, `queue_priority`
   - `ack_required`, `ack_deadline_minutes`
   - `status`, `trend`, `priority`
   - `operation`, `period`, `next_check_in_minutes`

### Fase 2.70 (implementada)

- Exportação CSV do monitoramento de SLA do ticket.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch.csv`)

### Fase 2.71 (implementada)

- Endpoint JSON de resumo de monitoramento do SLA.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload compacto com:
   - `watch_state`, `should_page`
   - `escalation_mode`, `follow_up_in_minutes`
   - `sla_status`, `breach_risk`
   - `ticket_type`, `ticket_state`, `ticket_severity`
   - `queue_name`, `queue_priority`
   - `ack_required`, `ack_deadline_minutes`
   - `status`, `trend`, `priority`
   - `operation`, `period`, `next_check_in_minutes`

### Fase 2.72 (implementada)

- Exportação CSV do resumo de monitoramento de SLA do ticket.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary.csv`)

### Fase 2.73 (implementada)

- Endpoint JSON de decisão executiva do monitoramento de SLA.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload compacto com:
   - `decision`, `action`
   - `watch_state`, `should_page`
   - `escalation_mode`, `follow_up_in_minutes`
   - `sla_status`, `breach_risk`
   - `ticket_type`, `ticket_state`, `ticket_severity`
   - `queue_name`, `queue_priority`
   - `ack_required`, `ack_deadline_minutes`
   - `status`, `trend`, `priority`
   - `operation`, `period`, `next_check_in_minutes`

### Fase 2.74 (implementada)

- Exportação CSV da decisão executiva de monitoramento de SLA.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision.csv`)

### Fase 2.75 (implementada)

- Endpoint JSON de despacho executivo da decisão de monitoramento.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload compacto com:
   - `dispatch_mode`, `notify_channel`
   - `decision`, `action`
   - `watch_state`, `should_page`
   - `escalation_mode`, `follow_up_in_minutes`
   - `sla_status`, `breach_risk`
   - `ticket_type`, `ticket_state`, `ticket_severity`
   - `queue_name`, `queue_priority`
   - `ack_required`, `ack_deadline_minutes`
   - `status`, `trend`, `priority`
   - `operation`, `period`, `next_check_in_minutes`

### Fase 2.76 (implementada)

- Exportação CSV do despacho executivo de monitoramento.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch.csv`)

### Fase 2.77 (implementada)

- Endpoint JSON de confirmação de despacho executivo.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/receipt`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Retorna payload compacto com:
   - `receipt_status`
   - `dispatch_mode`, `notify_channel`
   - `decision`, `action`
   - `watch_state`, `should_page`
   - `escalation_mode`, `follow_up_in_minutes`
   - `sla_status`, `breach_risk`
   - `ticket_type`, `ticket_state`, `ticket_severity`
   - `queue_name`, `queue_priority`
   - `ack_required`, `ack_deadline_minutes`
   - `status`, `trend`, `priority`
   - `operation`, `period`, `next_check_in_minutes`

### Fase 2.78 (implementada)

- Exportação CSV da confirmação de despacho executivo.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/receipt/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch_receipt.csv`)


### Fase 2.80 (implementada)

- Endpoint CSV de exportação da revisão da confirmação de despacho.
- Novo endpoint:
   - `GET /saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/receipt/review/export`
- Protegido por `X-Admin-Token`.
- Filtros suportados:
   - `from`
   - `to`
   - `operation`
- Formato de saída:
   - `text/csv`
   - download com `Content-Disposition` (`saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch_receipt_review.csv`)
  
Colunas:
   - `review_state`, `review_required`
   - `receipt_status`
   - `dispatch_mode`, `notify_channel`
   - `decision`, `action`
   - `watch_state`, `should_page`
   - `escalation_mode`, `follow_up_in_minutes`
   - `sla_status`, `breach_risk`
   - `ticket_type`, `ticket_state`, `ticket_severity`
   - `queue_name`, `queue_priority`
   - `owner`, `ack_required`, `ack_deadline_minutes`, `status`, `trend`, `priority`, `operation`, `period_from`, `period_to`, `next_check_in_minutes`
   - `ack_required`, `ack_deadline_minutes`
   - `status`, `trend`, `priority`
   - `operation`, `period`, `next_check_in_minutes`

### KPIs iniciais

- leads captados
- taxa de resposta da IA
- taxa de confirmação de reserva
- check-ins concluídos
- tempo médio de resposta
- conversão por origem (`meta`/`twilio`)

### Critérios de aceite

- KPIs retornam dados reais do período.
- Leads listados com estágio e origem.
- Funil exibe progressão por etapa.

---

## Fase 3 — Painel SaaS (Frontend MVP)

**Status:** Planejada

### Objetivos

- Demonstrar valor de negócio visualmente para hotelaria.
- Exibir resultado operacional sem depender de leitura técnica de logs.

### Escopo funcional

- Tela de overview com cards de KPI.
- Tabela de leads.
- Visualização simples de funil.
- Filtro por período e origem.

### Critérios de aceite

- Usuário de negócio entende performance sem apoio técnico.
- Dados do painel correspondem às APIs da Fase 2.

---

## Fase 4 — Pronto para Comercialização (Go-to-Market Técnico)

**Status:** Planejada

### Objetivos

- Tornar o produto operacionalmente seguro e vendável para múltiplos hotéis.
- Reduzir risco de operação em produção.

### Escopo técnico

- Autenticação e RBAC básico para painel.
- Multi-tenant inicial (separação por hotel/conta).
- Backup e restore documentados.
- Observabilidade mínima (logs estruturados e erros críticos).
- Rotina operacional de deploy e rollback.

### Indicadores de pronto para vender

- onboarding de novo hotel em fluxo padronizado
- métricas confiáveis por hotel
- operação com procedimento claro de suporte

---

## Notas de arquitetura

A evolução deve manter a arquitetura em camadas:

- `domain`: regras e contratos
- `application`: casos de uso e DTOs
- `infrastructure`: persistência, cache e integrações
- `interfaces`: API/webhooks

Não acoplar regras de negócio do funil/lead diretamente ao webhook.

---

## Próximos passos imediatos

1. Iniciar modelagem da Fase 2 (eventos + lead + KPIs).
2. Definir contrato de eventos para funil e métricas.
3. Publicar demo interna do painel ao fim da Fase 3.
