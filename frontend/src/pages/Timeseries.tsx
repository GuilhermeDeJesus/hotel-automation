import { useState } from "react";
import { useTimeseries } from "../hooks/useTimeseries";
import { useTenant } from "../contexts/TenantContext";
import Filters from "../components/Filters";
import TimeseriesChart from "../components/TimeseriesChart";
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";
import EmptyState from "../components/EmptyState";
import { IconInbox } from "../components/Icons";
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

export default function Timeseries() {
  const [filters, setFilters] = useState<DashboardFilters>(defaultFilters);
  const { data, error, isLoading, refetch } = useTimeseries(filters);
  const { hotelId } = useTenant();

  if (!hotelId) {
    return (
      <div>
        <h1 className="page-title">Evolução temporal</h1>
        <ErrorState message="Hotel não definido. Faça login novamente." onRetry={refetch} />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div>
        <h1 className="page-title">Evolução temporal</h1>
        <LoadingState variant="chart" message="Carregando série temporal..." />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1 className="page-title">Evolução temporal</h1>
        <ErrorState message={`Erro ao carregar dados: ${error}`} onRetry={refetch} />
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const points = data.points ?? [];
  const hasChartData = points.length > 0;

  return (
    <div>
      <h1 className="page-title">Evolução temporal</h1>
      <p
        style={{
          margin: "-0.75rem 0 1.5rem 0",
          color: "var(--color-text-muted)",
          fontSize: "0.9375rem",
        }}
      >
        Gráfico de evolução com leads, mensagens, reservas confirmadas e check-ins ao longo do
        tempo.
      </p>
      <Filters
        filters={filters}
        onChange={setFilters}
        showSource
        showStatus
        showGranularity
      />
      {hasChartData ? (
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
              Evolução no período
            </h2>
            {data.period && (
              <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                {data.period.from} a {data.period.to}
                {data.period.source ? ` • Origem: ${data.period.source}` : ""}
                {data.period.status ? ` • Estágio: ${data.period.status}` : ""}
                {` • Agrupamento: ${data.granularity === "week" ? "Semana" : data.granularity === "month" ? "Mês" : "Dia"}`}
              </span>
            )}
          </div>
          <TimeseriesChart data={points} granularity={data.granularity} />
        </div>
      ) : (
        <div className="card">
          <EmptyState
            title="Nenhum dado no período"
            description="Não há dados no período selecionado. Tente ajustar os filtros ou o intervalo de datas."
            icon={<IconInbox />}
          />
        </div>
      )}
    </div>
  );
}
