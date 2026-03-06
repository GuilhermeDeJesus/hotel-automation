import type { ReactNode } from "react";

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: ReactNode;
  icon?: ReactNode;
}

export default function KpiCard({ title, value, subtitle, icon }: KpiCardProps) {
  return (
    <div
      className="card"
      style={{
        padding: "1.5rem",
        minWidth: "180px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {icon && (
        <div
          style={{
            position: "absolute",
            top: "1rem",
            right: "1rem",
            opacity: 0.4,
            color: "var(--color-accent)",
          }}
        >
          {icon}
        </div>
      )}
      <div
        style={{
          color: "var(--color-text-muted)",
          fontSize: "0.8125rem",
          fontWeight: 500,
          marginBottom: "0.5rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        {title}
      </div>
      <div
        style={{
          fontSize: "1.75rem",
          fontWeight: 700,
          letterSpacing: "-0.02em",
          lineHeight: 1.2,
        }}
      >
        {value}
      </div>
      {subtitle && (
        <div
          style={{
            color: "var(--color-text-muted)",
            fontSize: "0.75rem",
            marginTop: "0.25rem",
          }}
        >
          {subtitle}
        </div>
      )}
    </div>
  );
}
