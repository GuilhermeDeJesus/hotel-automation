import type { DashboardFilters, SourceFilter, StatusFilter } from "../types/api";
import { IconFilter } from "./Icons";

interface FiltersProps {
  filters: DashboardFilters;
  onChange: (filters: DashboardFilters) => void;
  showSource?: boolean;
  showStatus?: boolean;
  showGranularity?: boolean;
}

function defaultDateRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 6);
  return {
    from: start.toISOString().slice(0, 10),
    to: end.toISOString().slice(0, 10),
  };
}

function toYMD(d: Date) {
  return d.toISOString().slice(0, 10);
}

const PERIOD_SHORTCUTS = [
  { label: "Hoje", getRange: () => { const t = new Date(); return { from: toYMD(t), to: toYMD(t) }; } },
  { label: "7 dias", getRange: () => { const end = new Date(); const start = new Date(); start.setDate(start.getDate() - 6); return { from: toYMD(start), to: toYMD(end) }; } },
  { label: "30 dias", getRange: () => { const end = new Date(); const start = new Date(); start.setDate(start.getDate() - 29); return { from: toYMD(start), to: toYMD(end) }; } },
  {
    label: "Este mês",
    getRange: () => {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth(), 1);
      return { from: toYMD(start), to: toYMD(now) };
    },
  },
] as const;

export default function Filters({
  filters,
  onChange,
  showSource = true,
  showStatus = false,
  showGranularity = false,
}: FiltersProps) {
  const { from, to } = defaultDateRange();
  const currentFrom = filters.from ?? from;
  const currentTo = filters.to ?? to;

  const handleChange = (updates: Partial<DashboardFilters>) => {
    onChange({ ...filters, ...updates });
  };

  const inputBase = {
    padding: "0.5rem 0.875rem",
    background: "var(--color-bg-elevated)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    color: "var(--color-text)",
    fontSize: "0.875rem",
    fontFamily: "inherit",
  };

  return (
    <div
      className="card"
      style={{
        padding: "1rem 1.25rem",
        marginBottom: "1.5rem",
        display: "flex",
        flexWrap: "wrap",
        gap: "1rem",
        alignItems: "center",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginRight: "0.5rem" }}>
        <span style={{ color: "var(--color-text-muted)" }}><IconFilter /></span>
        <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--color-text-muted)" }}>
          Filtros
        </span>
      </div>
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        {PERIOD_SHORTCUTS.map(({ label, getRange }) => (
          <button
            key={label}
            type="button"
            onClick={() => handleChange(getRange())}
            style={{
              padding: "0.375rem 0.75rem",
              fontSize: "0.8125rem",
              fontWeight: 500,
              background: "var(--color-bg-elevated)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              color: "var(--color-text-secondary)",
              cursor: "pointer",
              transition: "all 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "var(--color-surface-hover)";
              e.currentTarget.style.borderColor = "var(--color-border-light)";
              e.currentTarget.style.color = "var(--color-text)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "var(--color-bg-elevated)";
              e.currentTarget.style.borderColor = "var(--color-border)";
              e.currentTarget.style.color = "var(--color-text-secondary)";
            }}
          >
            {label}
          </button>
        ))}
      </div>
      <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>De</span>
        <input
          type="date"
          value={currentFrom}
          onChange={(e) => handleChange({ from: e.target.value })}
          style={inputBase}
        />
      </label>
      <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>Até</span>
        <input
          type="date"
          value={currentTo}
          onChange={(e) => handleChange({ to: e.target.value })}
          style={inputBase}
        />
      </label>
      {showSource && (
        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>Origem</span>
          <select
            value={filters.source ?? ""}
            onChange={(e) => handleChange({ source: e.target.value as SourceFilter })}
            style={{ ...inputBase, minWidth: 120 }}
          >
            <option value="">Todas</option>
            <option value="meta">Meta (WhatsApp)</option>
            <option value="twilio">Twilio</option>
          </select>
        </label>
      )}
      {showStatus && (
        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>Estágio</span>
          <select
            value={filters.status ?? ""}
            onChange={(e) => handleChange({ status: e.target.value as StatusFilter })}
            style={{ ...inputBase, minWidth: 160 }}
          >
            <option value="">Todos</option>
            <option value="NEW">Novo</option>
            <option value="ENGAGED">Engajado</option>
            <option value="RESERVATION_PENDING">Reserva pendente</option>
            <option value="RESERVATION_CONFIRMED">Reserva confirmada</option>
            <option value="CHECKED_IN">Check-in</option>
          </select>
        </label>
      )}
      {showGranularity && (
        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>Agrupamento</span>
          <select
            value={filters.granularity ?? "day"}
            onChange={(e) =>
              handleChange({ granularity: e.target.value as "day" | "week" | "month" })
            }
            style={{ ...inputBase, minWidth: 120 }}
          >
            <option value="day">Dia</option>
            <option value="week">Semana</option>
            <option value="month">Mês</option>
          </select>
        </label>
      )}
    </div>
  );
}
