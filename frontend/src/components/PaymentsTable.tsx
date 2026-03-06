import type { Payment, PaymentStatusType } from "../types/api";

interface PaymentsTableProps {
  payments: Payment[];
  onConfirm?: (id: string) => void;
  confirmLoadingId?: string | null;
}

const statusLabels: Record<string, string> = {
  PENDING: "Pendente",
  APPROVED: "Aprovado",
  REJECTED: "Rejeitado",
  EXPIRED: "Expirado",
  REFUNDED: "Estornado",
};

const statusColors: Record<string, { bg: string; text: string }> = {
  PENDING: { bg: "var(--color-warning-muted)", text: "var(--color-warning)" },
  APPROVED: { bg: "var(--color-success-muted)", text: "var(--color-success)" },
  REJECTED: { bg: "var(--color-error-muted)", text: "var(--color-error)" },
  EXPIRED: { bg: "var(--color-border)", text: "var(--color-text-muted)" },
  REFUNDED: { bg: "var(--color-border)", text: "var(--color-text-muted)" },
};

function formatDate(iso: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
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

function StatusBadge({ status }: { status: PaymentStatusType }) {
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

export default function PaymentsTable({
  payments,
  onConfirm,
  confirmLoadingId,
}: PaymentsTableProps) {
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
                ID Reserva
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
                Método
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
                Criado em
              </th>
              {onConfirm && (
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
            {payments.length === 0 ? (
              <tr>
                <td
                  colSpan={onConfirm ? 6 : 5}
                  style={{
                    padding: "3rem 1.25rem",
                    textAlign: "center",
                    color: "var(--color-text-muted)",
                  }}
                >
                  Nenhum pagamento encontrado
                </td>
              </tr>
            ) : (
              payments.map((p, i) => (
                <tr
                  key={p.id}
                  style={{
                    borderBottom: "1px solid var(--color-border)",
                    background: i % 2 === 1 ? "rgba(255,255,255,0.02)" : "transparent",
                  }}
                >
                  <td style={{ padding: "1rem 1.25rem", fontWeight: 500, fontFamily: "monospace", fontSize: "0.8125rem" }}>
                    {p.reservation_id}
                  </td>
                  <td style={{ padding: "1rem 1.25rem", color: "var(--color-text-secondary)" }}>
                    {formatCurrency(p.amount)}
                  </td>
                  <td style={{ padding: "1rem 1.25rem" }}>
                    <StatusBadge status={p.status} />
                  </td>
                  <td style={{ padding: "1rem 1.25rem", color: "var(--color-text-secondary)" }}>
                    {p.payment_method ?? "—"}
                  </td>
                  <td style={{ padding: "1rem 1.25rem", color: "var(--color-text-muted)", fontSize: "0.8125rem" }}>
                    {formatDate(p.created_at)}
                  </td>
                  {onConfirm && (
                    <td style={{ padding: "1rem 1.25rem", textAlign: "right" }}>
                      {p.status === "PENDING" && (
                        <button
                          type="button"
                          onClick={() => onConfirm(p.id)}
                          disabled={confirmLoadingId === p.id}
                          style={{
                            padding: "0.375rem 0.75rem",
                            fontSize: "0.75rem",
                            fontWeight: 500,
                            background: "var(--color-success-muted)",
                            border: "1px solid transparent",
                            borderRadius: "var(--radius-sm)",
                            color: "var(--color-success)",
                            cursor: confirmLoadingId === p.id ? "not-allowed" : "pointer",
                            opacity: confirmLoadingId === p.id ? 0.6 : 1,
                          }}
                        >
                          {confirmLoadingId === p.id ? "..." : "Confirmar pagamento"}
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
