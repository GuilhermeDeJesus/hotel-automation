import type { JourneyFunnelStage } from "../types/api";

interface JourneyFunnelChartProps {
  stages: JourneyFunnelStage[];
  total: number;
}

const stageGradients: Record<string, string> = {
  LEAD: "linear-gradient(90deg, #3b82f6 0%, #2563eb 100%)",
  RESERVA: "linear-gradient(90deg, #f59e0b 0%, #d97706 100%)",
  CONFIRMADA: "linear-gradient(90deg, #10b981 0%, #059669 100%)",
  CHECK_IN: "linear-gradient(90deg, #06b6d4 0%, #0891b2 100%)",
  CHECK_OUT: "linear-gradient(90deg, #34d399 0%, #10b981 100%)",
};

export default function JourneyFunnelChart({ stages, total }: JourneyFunnelChartProps) {
  const maxCount = Math.max(...stages.map((s) => s.count), 1);

  return (
    <div className="card" style={{ padding: "1.5rem", maxWidth: "640px" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h2 style={{ margin: "0 0 0.25rem 0", fontSize: "1rem", fontWeight: 600 }}>
          Funil da jornada completa
        </h2>
        <p style={{ margin: 0, fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
          Lead → Reserva → Confirmada → Check-in → Check-out
        </p>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {stages.map(({ stage, count, label }) => {
          const displayLabel = label ?? stage;
          const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
          const pctOfTotal = total > 0 ? ((count / total) * 100).toFixed(0) : "0";
          const gradient = stageGradients[stage] ?? "var(--color-accent)";
          return (
            <div key={stage}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "0.5rem",
                  fontSize: "0.875rem",
                }}
              >
                <span style={{ fontWeight: 500 }}>{displayLabel}</span>
                <span style={{ color: "var(--color-text-muted)", fontWeight: 600 }}>
                  {count}
                  {total > 0 && (
                    <span style={{ marginLeft: "0.5rem", fontWeight: 400 }}>
                      ({pctOfTotal}% {stage === "LEAD" ? "do total" : "dos leads"})
                    </span>
                  )}
                </span>
              </div>
              <div
                style={{
                  height: "32px",
                  background: "var(--color-bg-elevated)",
                  borderRadius: "var(--radius-sm)",
                  overflow: "hidden",
                  border: "1px solid var(--color-border)",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${Math.max(pct, count > 0 ? 2 : 0)}%`,
                    background: gradient,
                    borderRadius: "var(--radius-sm)",
                    transition: "width 0.4s ease",
                    minWidth: count > 0 ? "24px" : "0",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <div
        style={{
          marginTop: "1.5rem",
          paddingTop: "1rem",
          borderTop: "1px solid var(--color-border)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: "0.875rem",
        }}
      >
        <span style={{ color: "var(--color-text-muted)" }}>Total de leads</span>
        <span style={{ fontWeight: 700, fontSize: "1.125rem" }}>{total}</span>
      </div>
    </div>
  );
}
