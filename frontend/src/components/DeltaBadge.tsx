import { IconTrendingUp, IconTrendingDown, IconMinus } from "./Icons";
import type { KpiDelta } from "../types/api";

type MetricKey =
  | "leads_captured"
  | "ai_response_rate"
  | "reservation_confirmation_rate"
  | "checkins_completed"
  | "avg_response_time_seconds";

/** Para avg_response_time_seconds, menor é melhor. Para os demais, maior é melhor. */
const LOWER_IS_BETTER: MetricKey[] = ["avg_response_time_seconds"];

interface DeltaBadgeProps {
  delta: KpiDelta;
  metricKey: MetricKey;
  formatValue?: (absolute: number) => string;
}

export function DeltaBadge({
  delta,
  metricKey,
  formatValue = (n) => String(n),
}: DeltaBadgeProps) {
  const { absolute, percent } = delta;
  const isLowerBetter = LOWER_IS_BETTER.includes(metricKey);

  if (absolute === 0 && (percent === null || percent === 0)) {
    return (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.25rem",
          fontSize: "0.75rem",
          color: "var(--color-text-muted)",
          marginTop: "0.25rem",
        }}
      >
        <IconMinus />
        <span>vs período anterior</span>
      </span>
    );
  }

  const isPositive = absolute > 0;
  const isGood =
    isLowerBetter ? !isPositive : isPositive;
  const color = isGood ? "var(--color-success)" : "var(--color-error)";

  const percentStr =
    percent !== null ? ` (${percent > 0 ? "+" : ""}${percent.toFixed(1)}%)` : "";
  const prefix = absolute > 0 ? "+" : "";

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.25rem",
        fontSize: "0.75rem",
        color,
        marginTop: "0.25rem",
        fontWeight: 500,
      }}
    >
      {isPositive ? <IconTrendingUp /> : <IconTrendingDown />}
      <span>
        {prefix}
        {formatValue(absolute)}
        {percentStr} vs período anterior
      </span>
    </span>
  );
}
