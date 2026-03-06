import { useState } from "react";
import { useKpisCompare } from "../hooks/useKpisCompare";
import Filters from "../components/Filters";
import KpiCard from "../components/KpiCard";
import LeadsChart from "../components/LeadsChart";
import { DeltaBadge } from "../components/DeltaBadge";
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";
import {
  IconUsers,
  IconZap,
  IconCheckCircle,
  IconCalendar,
  IconClock,
  IconTrendingUp,
} from "../components/Icons";
import type { DashboardFilters } from "../types/api";

function defaultFilters(): DashboardFilters {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 6);
  return {
    from: start.toISOString().slice(0, 10),
    to: end.toISOString().slice(0, 10),
    granularity: "day",
  };
}

export default function Dashboard() {
  const [filters, setFilters] = useState<DashboardFilters>(defaultFilters);
  const { data, error, isLoading, refetch } = useKpisCompare(filters);

  if (isLoading) {
    return (
      <div>
        <h1 className="page-title">Overview</h1>
        <LoadingState variant="dashboard" message="Carregando métricas..." />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1 className="page-title">Overview</h1>
        <ErrorState message={`Erro ao carregar dados: ${error}`} onRetry={refetch} />
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const formatPercent = (n: number) => `${(n * 100).toFixed(1)}%`;
  const formatSeconds = (s: number) => `${s.toFixed(1)}s`;

  const current = data.current;
  const delta = data.delta;
  const period = data.current_period;
  const series = data.series_current ?? [];
  const hasChartData = series.length > 0;

  return (
    <div>
      <h1 className="page-title">Overview</h1>
      <Filters filters={filters} onChange={setFilters} showSource showStatus={false} showGranularity />

      {/* KPI Cards com comparação vs período anterior */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: "1.25rem",
          marginBottom: "2rem",
        }}
      >
        <KpiCard
          title="Leads captados"
          value={current.leads_captured}
          icon={<IconUsers />}
          subtitle={<DeltaBadge delta={delta.leads_captured} metricKey="leads_captured" />}
        />
        <KpiCard
          title="Taxa de resposta IA"
          value={formatPercent(current.ai_response_rate)}
          icon={<IconZap />}
          subtitle={
            <DeltaBadge
              delta={delta.ai_response_rate}
              metricKey="ai_response_rate"
              formatValue={(n: number) => `${(n * 100).toFixed(1)}pp`}
            />
          }
        />
        <KpiCard
          title="Taxa confirmação reserva"
          value={formatPercent(current.reservation_confirmation_rate)}
          icon={<IconCheckCircle />}
          subtitle={
            <DeltaBadge
              delta={delta.reservation_confirmation_rate}
              metricKey="reservation_confirmation_rate"
              formatValue={(n: number) => `${(n * 100).toFixed(1)}pp`}
            />
          }
        />
        <KpiCard
          title="Check-ins concluídos"
          value={current.checkins_completed}
          icon={<IconCalendar />}
          subtitle={<DeltaBadge delta={delta.checkins_completed} metricKey="checkins_completed" />}
        />
        <KpiCard
          title="Tempo médio resposta"
          value={formatSeconds(current.avg_response_time_seconds)}
          icon={<IconClock />}
          subtitle={
            <DeltaBadge
              delta={delta.avg_response_time_seconds}
              metricKey="avg_response_time_seconds"
              formatValue={(n: number) => `${n.toFixed(1)}s`}
            />
          }
        />
        <KpiCard
          title="Conversão por origem"
          value={
            Object.keys(current.conversion_by_source).length > 0
              ? Object.entries(current.conversion_by_source)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(" • ")
              : "—"
          }
          icon={<IconTrendingUp />}
        />
      </div>

      {/* Chart */}
      {hasChartData && (
        <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1rem",
            }}
          >
            <h2 style={{ margin: 0, fontSize: "1rem", fontWeight: 600 }}>
              Evolução de leads no período
            </h2>
            {period && (
              <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                {period.from} a {period.to}
                {period.source ? ` • Origem: ${period.source}` : ""}
                {data.granularity
                  ? ` • Agrupamento: ${data.granularity === "week" ? "Semana" : data.granularity === "month" ? "Mês" : "Dia"}`
                  : ""}
              </span>
            )}
          </div>
          <LeadsChart data={series} granularity={data.granularity} />
        </div>
      )}

      {period && !hasChartData && (
        <p style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
          Período: {period.from} a {period.to}
        </p>
      )}
    </div>
  );
}
