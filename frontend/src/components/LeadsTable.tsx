import type { Lead } from "../types/api";

interface LeadsTableProps {
  leads: Lead[];
}

const stageLabels: Record<string, string> = {
  NEW: "Novo",
  ENGAGED: "Engajado",
  RESERVATION_PENDING: "Reserva pendente",
  RESERVATION_CONFIRMED: "Reserva confirmada",
  CHECKED_IN: "Check-in",
};

const stageColors: Record<string, { bg: string; text: string }> = {
  NEW: { bg: "var(--color-accent-muted)", text: "var(--color-accent)" },
  ENGAGED: { bg: "rgba(6, 182, 212, 0.15)", text: "#06b6d4" },
  RESERVATION_PENDING: { bg: "var(--color-warning-muted)", text: "var(--color-warning)" },
  RESERVATION_CONFIRMED: { bg: "var(--color-success-muted)", text: "var(--color-success)" },
  CHECKED_IN: { bg: "rgba(16, 185, 129, 0.2)", text: "#34d399" },
};

function formatDate(iso: string | null) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("pt-BR", {
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

function StageBadge({ stage }: { stage: string }) {
  const colors = stageColors[stage] ?? { bg: "var(--color-border)", text: "var(--color-text-muted)" };
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
      {stageLabels[stage] ?? stage}
    </span>
  );
}

export default function LeadsTable({ leads }: LeadsTableProps) {
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
                Telefone
              </th>
              <th style={{ textAlign: "left", padding: "1rem 1.25rem", color: "var(--color-text-muted)", fontWeight: 600, fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Origem
              </th>
              <th style={{ textAlign: "left", padding: "1rem 1.25rem", color: "var(--color-text-muted)", fontWeight: 600, fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Estágio
              </th>
              <th style={{ textAlign: "left", padding: "1rem 1.25rem", color: "var(--color-text-muted)", fontWeight: 600, fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Mensagens
              </th>
              <th style={{ textAlign: "left", padding: "1rem 1.25rem", color: "var(--color-text-muted)", fontWeight: 600, fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Primeiro contato
              </th>
              <th style={{ textAlign: "left", padding: "1rem 1.25rem", color: "var(--color-text-muted)", fontWeight: 600, fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Último contato
              </th>
            </tr>
          </thead>
          <tbody>
            {leads.length === 0 ? (
              <tr>
                <td
                  colSpan={6}
                  style={{
                    padding: "3rem 1.25rem",
                    textAlign: "center",
                    color: "var(--color-text-muted)",
                  }}
                >
                  Nenhum lead encontrado no período selecionado
                </td>
              </tr>
            ) : (
              leads.map((lead, i) => (
                <tr
                  key={lead.id}
                  style={{
                    borderBottom: "1px solid var(--color-border)",
                    background: i % 2 === 1 ? "rgba(255,255,255,0.02)" : "transparent",
                  }}
                >
                  <td style={{ padding: "1rem 1.25rem", fontWeight: 500 }}>
                    {lead.phone_number}
                  </td>
                  <td style={{ padding: "1rem 1.25rem", color: "var(--color-text-secondary)" }}>
                    {lead.source === "meta" ? "Meta (WhatsApp)" : lead.source}
                  </td>
                  <td style={{ padding: "1rem 1.25rem" }}>
                    <StageBadge stage={lead.stage} />
                  </td>
                  <td style={{ padding: "1rem 1.25rem", color: "var(--color-text-secondary)" }}>
                    {lead.message_count}
                  </td>
                  <td style={{ padding: "1rem 1.25rem", color: "var(--color-text-muted)", fontSize: "0.8125rem" }}>
                    {formatDate(lead.first_seen_at)}
                  </td>
                  <td style={{ padding: "1rem 1.25rem", color: "var(--color-text-muted)", fontSize: "0.8125rem" }}>
                    {formatDate(lead.last_seen_at)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
