import type { ReservationsFilters as ReservationsFiltersType, ReservationStatus } from "../types/api";
import { IconFilter } from "./Icons";

interface ReservationsFiltersProps {
  filters: ReservationsFiltersType;
  onChange: (filters: ReservationsFiltersType) => void;
}

function toYMD(d: Date) {
  return d.toISOString().slice(0, 10);
}

function currentYearDateRange() {
  const now = new Date();
  const start = new Date(now.getFullYear(), 0, 1);
  const end = new Date(now.getFullYear(), 11, 31);
  return { from: toYMD(start), to: toYMD(end) };
}

function defaultDateRange() {
  return currentYearDateRange();
}

const PERIOD_SHORTCUTS = [
  { label: "Hoje", getRange: () => { const t = new Date(); return { from: toYMD(t), to: toYMD(t) }; } },
  { label: "7 dias", getRange: () => { const end = new Date(); const start = new Date(); start.setDate(start.getDate() - 6); return { from: toYMD(start), to: toYMD(end) }; } },
  { label: "30 dias", getRange: () => { const end = new Date(); const start = new Date(); start.setDate(start.getDate() - 29); return { from: toYMD(start), to: toYMD(end) }; } },
  { label: "Ano todo", getRange: () => currentYearDateRange() },
  {
    label: "Este mês",
    getRange: () => {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth(), 1);
      return { from: toYMD(start), to: toYMD(now) };
    },
  },
] as const;

const inputBase = {
  padding: "0.5rem 0.875rem",
  background: "var(--color-bg-elevated)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-sm)",
  color: "var(--color-text)",
  fontSize: "0.875rem",
  fontFamily: "inherit",
};

export default function ReservationsFilters({
  filters,
  onChange,
}: ReservationsFiltersProps) {
  const { from, to } = defaultDateRange();
  const currentFrom = filters.from ?? from;
  const currentTo = filters.to ?? to;

  const handleChange = (updates: Partial<ReservationsFiltersType>) => {
    onChange({ ...filters, ...updates });
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
      <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>Status</span>
        <select
          value={filters.status ?? ""}
          onChange={(e) => handleChange({ status: e.target.value as ReservationStatus | "" })}
          style={{ ...inputBase, minWidth: 140 }}
        >
          <option value="">Todos</option>
          <option value="PENDING">Pendente</option>
          <option value="CONFIRMED">Confirmada</option>
          <option value="CHECKED_IN">Check-in</option>
          <option value="CHECKED_OUT">Check-out</option>
          <option value="CANCELLED">Cancelada</option>
          <option value="NO_SHOW">No-show</option>
        </select>
      </label>
      <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>Quarto</span>
        <input
          type="text"
          placeholder="Ex: 101"
          value={filters.room_number ?? ""}
          onChange={(e) => handleChange({ room_number: e.target.value || undefined })}
          style={{ ...inputBase, width: 80 }}
        />
      </label>
    </div>
  );
}
