import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";
import type { SeriesPoint } from "../types/api";

interface LeadsChartProps {
  data: SeriesPoint[];
  height?: number;
  granularity?: string;
}

function formatDate(dateStr: string, granularity?: string) {
  const d = new Date(dateStr);
  if (granularity === "month") {
    return d.toLocaleDateString("pt-BR", { month: "short", year: "2-digit" });
  }
  if (granularity === "week") {
    return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
  }
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

export default function LeadsChart({ data, height = 280, granularity }: LeadsChartProps) {
  const chartData = data.map((p) => ({
    ...p,
    dateLabel: formatDate(p.date, granularity),
  }));

  const chartColor = "#3b82f6";

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorLeads" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={chartColor} stopOpacity={0.3} />
              <stop offset="95%" stopColor={chartColor} stopOpacity={0} />
            </linearGradient>
          </defs>
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
            formatter={(value: number) => [value, "Leads"]}
            labelFormatter={(label) => `Data: ${label}`}
          />
          <Area
            type="monotone"
            dataKey="leads"
            stroke={chartColor}
            strokeWidth={2}
            fill="url(#colorLeads)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
