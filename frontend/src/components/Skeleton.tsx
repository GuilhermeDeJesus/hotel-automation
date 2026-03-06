interface SkeletonProps {
  variant?: "text" | "circular" | "rectangular" | "card" | "table-row" | "chart";
  width?: string | number;
  height?: string | number;
  style?: React.CSSProperties;
}

export default function Skeleton({
  variant = "rectangular",
  width,
  height,
  style = {},
}: SkeletonProps) {
  const baseStyle: React.CSSProperties = {
    background: "linear-gradient(90deg, var(--color-border) 25%, var(--color-border-light) 50%, var(--color-border) 75%)",
    backgroundSize: "200% 100%",
    animation: "skeleton-shimmer 1.5s ease-in-out infinite",
    borderRadius: variant === "circular" ? "50%" : "var(--radius-sm)",
    ...(width && { width: typeof width === "number" ? `${width}px` : width }),
    ...(height && { height: typeof height === "number" ? `${height}px` : height }),
    ...style,
  };

  return <div style={baseStyle} aria-hidden />;
}

export function SkeletonCard() {
  return (
    <div className="card" style={{ padding: "1.5rem" }}>
      <Skeleton variant="text" height={20} width="60%" style={{ marginBottom: "0.75rem" }} />
      <Skeleton variant="text" height={14} width="90%" style={{ marginBottom: "1rem" }} />
      <Skeleton variant="rectangular" height={48} />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="card" style={{ overflow: "hidden" }}>
      <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid var(--color-border)" }}>
        <Skeleton variant="text" height={14} width="100%" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            gap: "1rem",
            padding: "1rem 1.25rem",
            borderBottom: i < rows - 1 ? "1px solid var(--color-border)" : "none",
          }}
        >
          <Skeleton variant="text" height={16} width="15%" />
          <Skeleton variant="text" height={16} width="25%" />
          <Skeleton variant="text" height={16} width="20%" />
          <Skeleton variant="text" height={16} width="15%" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="card" style={{ padding: "1.5rem" }}>
      <Skeleton variant="text" height={18} width="40%" style={{ marginBottom: "1rem" }} />
      <Skeleton variant="rectangular" height={200} style={{ marginBottom: "1rem" }} />
      <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem" }}>
        {[60, 80, 45, 90, 70].map((w, i) => (
          <Skeleton key={i} variant="rectangular" height={24} width={`${w}%`} />
        ))}
      </div>
    </div>
  );
}
