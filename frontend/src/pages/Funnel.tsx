import { useState } from "react";
import { useFunnel } from "../hooks/useFunnel";
import { useJourneyFunnel } from "../hooks/useJourneyFunnel";
import Filters from "../components/Filters";
import FunnelChart from "../components/FunnelChart";
import JourneyFunnelChart from "../components/JourneyFunnelChart";
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";
import { downloadCsv } from "../utils/csvExport";
import type { DashboardFilters, FunnelStage } from "../types/api";

function defaultFilters(): DashboardFilters {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 6);
  return {
    from: start.toISOString().slice(0, 10),
    to: end.toISOString().slice(0, 10),
  };
}

export default function Funnel() {
  const [filters, setFilters] = useState<DashboardFilters>(defaultFilters);
  const { data, error, isLoading, refetch: refetchFunnel } = useFunnel(filters);
  const {
    data: journeyData,
    error: journeyError,
    isLoading: journeyLoading,
    refetch: refetchJourney,
  } = useJourneyFunnel(filters);

  const anyLoading = isLoading || journeyLoading;
  const anyError = error || journeyError;
  const refetch = () => {
    refetchFunnel();
    refetchJourney();
  };

  if (anyLoading) {
    return (
      <div>
        <h1 className="page-title">Funil de conversão</h1>
        <LoadingState variant="funnel" message="Carregando funis..." />
      </div>
    );
  }

  if (anyError) {
    return (
      <div>
        <h1 className="page-title">Funil de conversão</h1>
        <ErrorState message={`Erro ao carregar: ${anyError}`} onRetry={refetch} />
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const handleExportCsv = () => {
    const rows: Record<string, string | number | null | undefined>[] = data!.stages.map(
      (s: FunnelStage) => ({
        estagio: s.stage,
        quantidade: s.count,
      })
    );
    if (rows.length > 0) {
      rows.push({ estagio: "TOTAL", quantidade: data!.total });
    }
    const from = filters.from ?? "";
    const to = filters.to ?? "";
    const filename = `funil_${from}_${to}.csv`;
    downloadCsv(rows, filename, ["estagio", "quantidade"]);
  };

  const handleExportJourneyCsv = () => {
    if (!journeyData) return;
    const rows: Record<string, string | number | null | undefined>[] = journeyData.stages.map(
      (s) => ({
        estagio: s.label ?? s.stage,
        quantidade: s.count,
      })
    );
    if (rows.length > 0) {
      rows.push({ estagio: "TOTAL LEADS", quantidade: journeyData.total });
    }
    const from = filters.from ?? "";
    const to = filters.to ?? "";
    const filename = `funil_jornada_${from}_${to}.csv`;
    downloadCsv(rows, filename, ["estagio", "quantidade"]);
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem", marginBottom: "1.5rem" }}>
        <div>
          <h1 className="page-title" style={{ marginBottom: "0.25rem" }}>Funil de conversão</h1>
          <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "0.9375rem" }}>
            Funil de leads e jornada completa (Lead → Reserva → Check-out).
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            type="button"
            onClick={handleExportCsv}
            disabled={!data || data.stages.length === 0}
          style={{
            padding: "0.5rem 1rem",
            fontSize: "0.875rem",
            fontWeight: 500,
            background: "var(--color-bg-elevated)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            color: "var(--color-text-secondary)",
            cursor: !data || data.stages.length === 0 ? "not-allowed" : "pointer",
            opacity: !data || data.stages.length === 0 ? 0.6 : 1,
          }}
          >
            Exportar CSV (leads)
          </button>
          <button
            type="button"
            onClick={handleExportJourneyCsv}
            disabled={!journeyData || journeyData.stages.length === 0}
            style={{
              padding: "0.5rem 1rem",
              fontSize: "0.875rem",
              fontWeight: 500,
              background: "var(--color-bg-elevated)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              color: "var(--color-text-secondary)",
              cursor: !journeyData || journeyData.stages.length === 0 ? "not-allowed" : "pointer",
              opacity: !journeyData || journeyData.stages.length === 0 ? 0.6 : 1,
            }}
          >
            Exportar CSV (jornada)
          </button>
        </div>
      </div>
      <Filters filters={filters} onChange={setFilters} showSource={false} showStatus={false} />
      <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
        <FunnelChart stages={data!.stages} total={data!.total} />
        <JourneyFunnelChart stages={journeyData?.stages ?? []} total={journeyData?.total ?? 0} />
      </div>
    </div>
  );
}
