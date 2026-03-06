import type { PaymentsFilters as PaymentsFiltersType, PaymentStatusType } from "../types/api";
import { IconFilter } from "./Icons";

interface PaymentsFiltersProps {
  filters: PaymentsFiltersType;
  onChange: (filters: PaymentsFiltersType) => void;
}

const inputBase = {
  padding: "0.5rem 0.875rem",
  background: "var(--color-bg-elevated)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-sm)",
  color: "var(--color-text)",
  fontSize: "0.875rem",
  fontFamily: "inherit",
};

export default function PaymentsFilters({
  filters,
  onChange,
}: PaymentsFiltersProps) {
  const handleChange = (updates: Partial<PaymentsFiltersType>) => {
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
      <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>ID Reserva</span>
        <input
          type="text"
          placeholder="Filtrar por reserva"
          value={filters.reservation_id ?? ""}
          onChange={(e) => handleChange({ reservation_id: e.target.value || undefined })}
          style={{ ...inputBase, width: 180, fontFamily: "monospace" }}
        />
      </label>
      <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>Status</span>
        <select
          value={filters.status ?? ""}
          onChange={(e) => handleChange({ status: e.target.value as PaymentStatusType | "" })}
          style={{ ...inputBase, minWidth: 140 }}
        >
          <option value="">Todos</option>
          <option value="PENDING">Pendente</option>
          <option value="APPROVED">Aprovado</option>
          <option value="REJECTED">Rejeitado</option>
          <option value="EXPIRED">Expirado</option>
          <option value="REFUNDED">Estornado</option>
        </select>
      </label>
    </div>
  );
}
