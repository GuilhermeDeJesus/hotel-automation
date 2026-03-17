import { useState } from "react";
import { useLeads } from "../hooks/useLeads";
import { useTenant } from "../contexts/TenantContext";
import Filters from "../components/Filters";
import LeadsTable from "../components/LeadsTable";
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";
import EmptyState from "../components/EmptyState";
import { downloadCsv } from "../utils/csvExport";
import { IconInbox } from "../components/Icons";
import type { DashboardFilters, Lead } from "../types/api";

function defaultFilters(): DashboardFilters {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 6);
  return {
    from: start.toISOString().slice(0, 10),
    to: end.toISOString().slice(0, 10),
  };
}

export default function Leads() {
  const [filters, setFilters] = useState<DashboardFilters>(defaultFilters);
  const { data, error, isLoading, refetch } = useLeads(filters);
  const { hotelId } = useTenant();

  if (!hotelId) {
    return (
      <div>
        <h1 className="page-title">Leads</h1>
        <ErrorState message="Hotel não definido. Faça login novamente." onRetry={refetch} />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div>
        <h1 className="page-title">Leads</h1>
        <LoadingState variant="table" message="Carregando leads..." />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1 className="page-title">Leads</h1>
        <ErrorState message={`Erro ao carregar leads: ${error}`} onRetry={refetch} />
      </div>
    );
  }

  const leads = data?.items ?? [];

  const handleExportCsv = () => {
    const rows: Record<string, string | number | null | undefined>[] = leads.map((l: Lead) => ({
      id: l.id,
      telefone: l.phone_number,
      origem: l.source,
      estagio: l.stage,
      mensagens: l.message_count,
      primeiro_contato: l.first_seen_at ?? "",
      ultimo_contato: l.last_seen_at ?? "",
    }));
    const from = filters.from ?? "";
    const to = filters.to ?? "";
    const filename = `leads_${from}_${to}.csv`;
    downloadCsv(rows, filename, ["id", "telefone", "origem", "estagio", "mensagens", "primeiro_contato", "ultimo_contato"]);
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem", marginBottom: "1.5rem" }}>
        <div>
          <h1 className="page-title" style={{ marginBottom: "0.25rem" }}>Leads</h1>
          <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "0.9375rem" }}>
            Lista completa de leads captados via WhatsApp com filtros por período, origem e estágio.
          </p>
        </div>
        <button
          type="button"
          onClick={handleExportCsv}
          disabled={leads.length === 0}
          style={{
            padding: "0.5rem 1rem",
            fontSize: "0.875rem",
            fontWeight: 500,
            background: "var(--color-bg-elevated)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            color: "var(--color-text-secondary)",
            cursor: leads.length === 0 ? "not-allowed" : "pointer",
            opacity: leads.length === 0 ? 0.6 : 1,
          }}
        >
          Exportar CSV
        </button>
      </div>
      <Filters filters={filters} onChange={setFilters} showSource showStatus />
      {leads.length === 0 ? (
        <div className="card">
          <EmptyState
            title="Nenhum lead encontrado"
            description="Não há leads no período selecionado. Tente ajustar os filtros."
            icon={<IconInbox />}
          />
        </div>
      ) : (
        <LeadsTable leads={leads} />
      )}
    </div>
  );
}
