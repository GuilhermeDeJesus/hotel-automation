import type { Reservation, ReservationStatus } from "../types/api";

interface ReservationsTableProps {
  reservations: Reservation[];
  onMarkNoShow?: (id: string) => void;
  markNoShowLoadingId?: string | null;
}

const statusLabels: Record<string, string> = {
  PENDING: "Pendente",
  CONFIRMED: "Confirmada",
  CHECKED_IN: "Check-in",
  CHECKED_OUT: "Check-out",
  CANCELLED: "Cancelada",
  NO_SHOW: "No-show",
};

const statusColors: Record<string, { bg: string; text: string }> = {
  PENDING: { bg: "var(--color-warning-muted)", text: "var(--color-warning)" },
  CONFIRMED: { bg: "var(--color-success-muted)", text: "var(--color-success)" },
  CHECKED_IN: { bg: "rgba(6, 182, 212, 0.15)", text: "#06b6d4" },
  CHECKED_OUT: { bg: "var(--color-border)", text: "var(--color-text-muted)" },
  CANCELLED: { bg: "var(--color-error-muted)", text: "var(--color-error)" },
  NO_SHOW: { bg: "var(--color-error-muted)", text: "var(--color-error)" },
};

function formatDate(iso: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

function StatusBadge({ status }: { status: ReservationStatus }) {
  const colors = statusColors[status] ?? {
    bg: "var(--color-border)",
    text: "var(--color-text-muted)",
  };
  return (
    <span
      style={{
        display: "inline-block",
        padding: "0.25rem 0.625rem",
        borderRadius: "9999px",
        fontSize: "0.75rem",
        fontWeight: 600,
        background: colors.bg,
        color: colors.text,
      }}
    >
      {statusLabels[status] ?? status}
    </span>
  );
}

export default function ReservationsTable({
  reservations,
  onMarkNoShow,
  markNoShowLoadingId,
}: ReservationsTableProps) {
  return (
    <div className="card" style={{ overflow: "hidden" }}>
      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "0.875rem",
          }}
        >
          <thead>
            <tr style={{ background: "var(--color-bg-elevated)" }}>
              <th
                style={{
                  textAlign: "left",
                  padding: "1rem 1.25rem",
                  color: "var(--color-text-muted)",
                  fontWeight: 600,
                  fontSize: "0.75rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Hóspede
              </th>
              <th
                style={{
                  textAlign: "left",
                  padding: "1rem 1.25rem",
                  color: "var(--color-text-muted)",
                  fontWeight: 600,
                  fontSize: "0.75rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Status
              </th>
              <th
                style={{
                  textAlign: "left",
                  padding: "1rem 1.25rem",
                  color: "var(--color-text-muted)",
                  fontWeight: 600,
                  fontSize: "0.75rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Check-in
              </th>
              <th
                style={{
                  textAlign: "left",
                  padding: "1rem 1.25rem",
                  color: "var(--color-text-muted)",
                  fontWeight: 600,
                  fontSize: "0.75rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Check-out
              </th>
              <th
                style={{
                  textAlign: "left",
                  padding: "1rem 1.25rem",
                  color: "var(--color-text-muted)",
                  fontWeight: 600,
                  fontSize: "0.75rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Quarto
              </th>
              <th
                style={{
                  textAlign: "left",
                  padding: "1rem 1.25rem",
                  color: "var(--color-text-muted)",
                  fontWeight: 600,
                  fontSize: "0.75rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Valor
              </th>
              {onMarkNoShow && (
                <th
                  style={{
                    textAlign: "right",
                    padding: "1rem 1.25rem",
                    color: "var(--color-text-muted)",
                    fontWeight: 600,
                    fontSize: "0.75rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  Ações
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {reservations.length === 0 ? (
              <tr>
                <td
                  colSpan={onMarkNoShow ? 7 : 6}
                  style={{
                    padding: "3rem 1.25rem",
                    textAlign: "center",
                    color: "var(--color-text-muted)",
                  }}
                >
                  Nenhuma reserva encontrada
                </td>
              </tr>
            ) : (
              reservations.map((r, i) => (
                <tr
                  key={r.id}
                  style={{
                    borderBottom: "1px solid var(--color-border)",
                    background: i % 2 === 1 ? "rgba(255,255,255,0.02)" : "transparent",
                  }}
                >
                  <td style={{ padding: "1rem 1.25rem", fontWeight: 500 }}>
                    <div>{r.guest_name}</div>
                    <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                      {r.guest_phone}
                    </div>
                  </td>
                  <td style={{ padding: "1rem 1.25rem" }}>
                    <StatusBadge status={r.status} />
                  </td>
                  <td style={{ padding: "1rem 1.25rem", color: "var(--color-text-secondary)" }}>
                    {formatDate(r.check_in_date)}
                  </td>
                  <td style={{ padding: "1rem 1.25rem", color: "var(--color-text-secondary)" }}>
                    {formatDate(r.check_out_date)}
                  </td>
                  <td style={{ padding: "1rem 1.25rem", color: "var(--color-text-secondary)" }}>
                    {r.room_number ?? "—"}
                  </td>
                  <td style={{ padding: "1rem 1.25rem", color: "var(--color-text-secondary)" }}>
                    {formatCurrency(r.total_amount)}
                  </td>
                  {onMarkNoShow && (
                    <td style={{ padding: "1rem 1.25rem", textAlign: "right" }}>
                      {r.status === "CONFIRMED" && (
                        <button
                          type="button"
                          onClick={() => onMarkNoShow(r.id)}
                          disabled={markNoShowLoadingId === r.id}
                          style={{
                            padding: "0.375rem 0.75rem",
                            fontSize: "0.75rem",
                            fontWeight: 500,
                            background: "var(--color-error-muted)",
                            border: "1px solid transparent",
                            borderRadius: "var(--radius-sm)",
                            color: "var(--color-error)",
                            cursor: markNoShowLoadingId === r.id ? "not-allowed" : "pointer",
                            opacity: markNoShowLoadingId === r.id ? 0.6 : 1,
                          }}
                        >
                          {markNoShowLoadingId === r.id ? "..." : "Marcar no-show"}
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
