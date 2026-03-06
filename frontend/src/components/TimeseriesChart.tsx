import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ComposedChart,
  Line,
  Legend,
} from "recharts";
import type { SeriesPoint } from "../types/api";

interface TimeseriesChartProps {
  data: SeriesPoint[];
  height?: number;
  granularity?: string;
  /** Série ativa para exibição (todas por padrão) */
  activeSeries?: string[];
}

const SERIES_CONFIG = [
  { key: "leads", label: "Leads", color: "#3b82f6" },
  { key: "inbound_messages", label: "Mensagens entrada", color: "#10b981" },
  { key: "outbound_messages", label: "Mensagens saída", color: "#8b5cf6" },
  { key: "confirmed_reservations", label: "Reservas confirmadas", color: "#f59e0b" },
  { key: "checkins", label: "Check-ins", color: "#06b6d4" },
] as const;

function formatDate(dateStr: string, granularity: string) {
  const d = new Date(dateStr);
  if (granularity === "month") {
    return d.toLocaleDateString("pt-BR", { month: "short", year: "2-digit" });
  }
  if (granularity === "week") {
    return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
  }
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

export default function TimeseriesChart({
  data,
  height = 360,
  granularity = "day",
  activeSeries,
}: TimeseriesChartProps) {
  const active = activeSeries ?? SERIES_CONFIG.map((s) => s.key);
  const chartData = data.map((p) => ({
    ...p,
    dateLabel: formatDate(p.date, granularity),
  }));

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" opacity={0.5} />
          <XAxis
            dataKey="dateLabel"
            stroke="var(--color-text-muted)"
            fontSize={11}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="var(--color-text-muted)"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => (v >= 1000 ? `${v / 1000}k` : v)}
          />
          <Tooltip
            contentStyle={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              color: "var(--color-text)",
            }}
            labelStyle={{ color: "var(--color-text-muted)" }}
            labelFormatter={(label) => `Data: ${label}`}
          />
          <Legend
            wrapperStyle={{ fontSize: "0.8125rem" }}
            formatter={(value) => (
              <span style={{ color: "var(--color-text-secondary)" }}>{value}</span>
            )}
          />
          {SERIES_CONFIG.filter((s) => active.includes(s.key)).map(({ key, label, color }) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              name={label}
              stroke={color}
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
