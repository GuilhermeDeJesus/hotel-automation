# Roadmap de Implementações — Frontend

Este documento descreve as implementações planejadas para o frontend do Hotel Automation, com base na análise do backend (`app/`), da documentação de orquestração (`docs/MELHORIAS_ORQUESTRACAO_RESERVACAO.md`) e do estado atual do painel.

---

## Índice

1. [Contexto e estado atual](#1-contexto-e-estado-atual)
2. [Itens de implementação](#2-itens-de-implementação)
3. [Ordem de implementação](#3-ordem-de-implementação)
4. [Dependências de API](#4-dependências-de-api)

---

## 1. Contexto e estado atual

### 1.1 Backend disponível

| API | Endpoint | Status |
|-----|----------|--------|
| KPIs | `GET /saas/kpis` | ✅ Consumido |
| Leads | `GET /saas/leads` | ✅ Consumido |
| Funnel | `GET /saas/funnel` | ✅ Consumido |
| Timeseries | `GET /saas/timeseries` | ✅ Consumido |
| KPIs Compare | `GET /saas/kpis/compare` | ❌ Não consumido |
| Cache Invalidate | `POST /saas/cache/invalidate` | ✅ Consumido |
| Audit Events | `GET /saas/audit-events/*` | ✅ Consumido |

### 1.2 Páginas atuais

- **Overview (Dashboard):** KPIs + gráfico de evolução de leads
- **Leads:** Tabela de leads com filtros
- **Funnel:** Funil de conversão

### 1.3 Jornada do hóspede (backend)

O backend implementa a jornada completa via WhatsApp:

- Criação de reserva, confirmação, check-in, check-out, cancelamento, extensão
- Pré-check-in, pagamento (Stripe/Manual), pedidos de quarto, suporte
- Comunicação proativa, no-show

**Não há API REST CRUD** para reservas, quartos ou hotéis — o fluxo é via WhatsApp.

---

## 2. Itens de implementação

### Item 1 — Comparação de períodos no Dashboard ✅ (implementado)

**Objetivo:** Mostrar variação dos KPIs em relação ao período anterior.

**API:** `GET /saas/kpis/compare?from=...&to=...&source=...&status=...&granularity=...`

**Resposta:**
```json
{
  "current": { "leads_captured": 42, "ai_response_rate": 0.95, ... },
  "previous": { "leads_captured": 36, ... },
  "delta": {
    "leads_captured": { "absolute": 6, "percent": 16.667 },
    ...
  },
  "current_period": { "from": "...", "to": "..." },
  "previous_period": { "from": "...", "to": "..." }
}
```

**Implementação:**
- Hook `useKpisCompare` consumindo a API
- KpiCard com `subtitle` opcional para exibir delta (ex.: "+15% vs período anterior")
- Indicador visual de tendência (↑ verde, ↓ vermelho, — neutro)

**Critério de aceite:** Cards de KPI exibem valor atual + variação percentual em relação ao período anterior equivalente.

---

### Item 2 — Página Timeseries ✅ (implementado)

**Objetivo:** Gráfico de evolução temporal com filtros.

**API:** `GET /saas/timeseries?from=...&to=...&source=...&status=...&granularity=...`

**Implementação:**
- Nova rota `/timeseries`
- Hook `useTimeseries` com suporte a granularidade
- Gráfico com múltiplas séries (leads, mensagens entrada/saída, reservas confirmadas, check-ins)
- Filtros: período, origem, status, granularidade (day/week/month)

**Critério de aceite:** Página exibe gráfico de evolução com dados da API.

---

### Item 3 — Filtro de granularidade ✅ (implementado)

**Objetivo:** Permitir visualização por dia, semana ou mês.

**Implementação:**
- Seletor `granularity` nos componentes Filters (showGranularity)
- Valores: `day`, `week`, `month`
- Dashboard e Timeseries passam granularidade para kpis/compare e timeseries
- LeadsChart e TimeseriesChart formatam labels do eixo X conforme granularidade

**Critério de aceite:** Usuário pode alternar entre granularidade diária, semanal e mensal.

---

### Item 4 — Atalhos de período nos filtros ✅ (implementado)

**Objetivo:** Seleção rápida de períodos comuns.

**Implementação:**
- Botões: "Hoje", "7 dias", "30 dias", "Este mês"
- Ao clicar, atualiza `from` e `to` nos filtros
- Integrado ao componente Filters (todas as páginas que usam filtros)

**Critério de aceite:** Filtros permitem seleção rápida de período.

---

### Item 5 — API + Painel de reservas ✅ (implementado)

**Objetivo:** Listar e gerenciar reservas.

**Implementação:**
- API `GET /saas/reservations` com filtros: from, to, status, room_number
- API `POST /saas/reservations/{id}/mark-no-show` para marcar no-show
- Painel em `/reservations` com tabela, filtros e ação marcar no-show
- Use cases: ListReservationsUseCase, MarkNoShowReservationUseCase

**Critério de aceite:** Painel operacional de reservas funcional.

---

### Item 6 — API + Painel de pagamentos ✅ (implementado)

**Objetivo:** Listar pagamentos e confirmar manualmente.

**Implementação:**
- API `GET /saas/payments` com filtros: reservation_id, status
- API `POST /saas/payments/{id}/confirm` para confirmação manual (Fase 0)
- Painel em `/payments` com tabela, filtros e ação confirmar pagamento
- Use cases: ListPaymentsUseCase, ConfirmPaymentManualUseCase
- Ao confirmar, reserva PENDING associada é confirmada automaticamente

**Critério de aceite:** Painel de pagamentos funcional.

---

### Item 7 — Export CSV (Leads, Funnel) ✅ (implementado)

**Objetivo:** Exportar dados em CSV.

**Implementação:**
- Botão "Exportar CSV" em Leads e Funnel
- Utilitário `downloadCsv` em `src/utils/csvExport.ts` — gera CSV no cliente e dispara download
- Leads: colunas id, telefone, origem, estágio, mensagens, primeiro_contato, ultimo_contato
- Funil: colunas estágio, quantidade + linha TOTAL

**Critério de aceite:** Usuário pode baixar CSV dos leads e do funil.

---

### Item 8 — Configuração do hotel ✅ (implementado)

**Objetivo:** Editar configurações de pagamento.

**Implementação:**
- API `GET /saas/hotel/config` — retorna config do hotel ativo
- API `PATCH /saas/hotel/config` — atualiza `requires_payment_for_confirmation`, `allows_reservation_without_payment`
- Página `/hotel-config` com checkboxes e botão Salvar
- Use cases: GetHotelConfigUseCase, UpdateHotelConfigUseCase

**Critério de aceite:** Configuração de hotel editável via painel.

---

### Item 9 — Painel de auditoria (admin) ✅ (implementado)

**Objetivo:** Visualizar eventos de auditoria.

**API:** `GET /saas/audit-events` (requer `X-Admin-Token`).

**Implementação:**
- Página `/admin/audit` com rota registrada e item no menu
- Token admin via `VITE_SAAS_ADMIN_TOKEN` ou input na página (sessionStorage)
- Hook `useAuditEvents` com parâmetro `enabled` para evitar chamadas sem token
- Filtros: from, to, outcome; tabela de eventos; paginação
- Ícone `IconAudit` no menu

**Critério de aceite:** Admin pode visualizar eventos de auditoria.

---

### Item 10 — Invalidação de cache ✅ (implementado)

**Objetivo:** Botão para forçar atualização dos dados.

**API:** `POST /saas/cache/invalidate` (requer `X-Admin-Token`).

**Implementação:**
- Botão "Atualizar dados" no header (Layout)
- Função `invalidateCache()` no client com token admin
- Feedback de sucesso (recarrega página) ou erro (mensagem inline)
- Ícone `IconRefresh` no botão

**Critério de aceite:** Admin pode invalidar cache manualmente.

---

### Item 11 — Funil da jornada completa ✅ (implementado)

**Objetivo:** Funil estendido (Lead → Reserva → Confirmada → Check-in → Check-out).

**Implementação:**
- API `GET /saas/funnel/journey` — agrega leads (saas_repository) + reservas (reservation_repository)
- Use case `GetJourneyFunnelUseCase` e `count_by_status` no repositório de reservas
- Página Funnel: segundo card "Funil da jornada completa" com `JourneyFunnelChart`
- Hook `useJourneyFunnel` e export CSV da jornada

**Critério de aceite:** Funil mostra estágios completos da jornada.

---

### Item 12 — Melhorias de UX ✅ (implementado)

**Objetivo:** Aprimorar experiência do usuário.

**Implementações:**
- Skeleton em vez de spinner genérico — `Skeleton`, `LoadingState` com variantes (dashboard, table, chart, funnel)
- Retry em caso de erro — `ErrorState` com botão "Tentar novamente" em todas as páginas
- Toast para feedback de ações — `ToastContext`, `useToast`, usado em cache invalidation e HotelConfig
- Sidebar colapsável em mobile — hamburger no header, overlay, fecha ao navegar
- Dark mode (toggle de tema) — `ThemeContext`, toggle sol/lua no header, persistência em localStorage
- Empty states — `EmptyState` com ícone em Leads, Reservations, Payments, Timeseries

---

## 3. Ordem de implementação

| # | Item | Esforço | Impacto | Status |
|---|------|---------|---------|--------|
| 1 | Comparação de períodos no Dashboard | Baixo | Alto | ✅ Concluído |
| 2 | Página Timeseries | Baixo | Alto | ✅ Concluído |
| 3 | Filtro de granularidade | Baixo | Médio | ✅ Concluído |
| 4 | Atalhos de período nos filtros | Baixo | Médio | ✅ Concluído |
| 5 | API + Painel de reservas | Alto | Muito alto | ✅ Concluído |
| 6 | API + Painel de pagamentos | Médio | Alto | ✅ Concluído |
| 7 | Export CSV (Leads, Funnel) | Baixo | Médio | ✅ Concluído |
| 8 | Configuração do hotel | Médio | Médio | ✅ Concluído |
| 9 | Painel de auditoria (admin) | Médio | Baixo | ✅ Concluído |
| 10 | Invalidação de cache | Baixo | Baixo | ✅ Concluído |
| 11 | Funil da jornada completa | Médio | Médio | ✅ Concluído |
| 12 | Melhorias de UX | Variado | Médio | ✅ Concluído |

---

## 4. Dependências de API

| Item | Endpoint existente | Novo endpoint necessário |
|------|--------------------|---------------------------|
| 1 | `GET /saas/kpis/compare` | — |
| 2 | `GET /saas/timeseries` | — |
| 3 | — | — (parâmetro `granularity`) |
| 4 | — | — |
| 5 | — | `GET /saas/reservations` ou similar |
| 6 | — | `GET /saas/payments` |
| 7 | — | Opcional: endpoint de export |
| 8 | — | `GET/PATCH /hotels/:id/config` |
| 9 | `GET /saas/audit-events` | — |
| 10 | `POST /saas/cache/invalidate` | — |
| 11 | `GET /saas/funnel/journey` | — |

---

## Documentos relacionados

- `docs/MELHORIAS_ORQUESTRACAO_RESERVACAO.md` — Jornada do hóspede e melhorias
- `docs/SAAS_MVP_4_FASES.md` — Roadmap SaaS
- `.cursor/rules/frontend-backend-boundary.mdc` — Regras de fronteira frontend/backend
