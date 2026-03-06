import { SkeletonCard, SkeletonTable, SkeletonChart } from "./Skeleton";

type Variant = "dashboard" | "table" | "chart" | "funnel";

interface LoadingStateProps {
  variant?: Variant;
  message?: string;
}

export default function LoadingState({ variant = "dashboard", message }: LoadingStateProps) {
  return (
    <div style={{ minHeight: 200 }}>
      {variant === "dashboard" && (
        <div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
              gap: "1.25rem",
              marginBottom: "2rem",
            }}
          >
            {[1, 2, 3, 4, 5].map((i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
          <SkeletonChart />
        </div>
      )}
      {variant === "table" && <SkeletonTable rows={8} />}
      {variant === "chart" && <SkeletonChart />}
      {variant === "funnel" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
          <SkeletonChart />
          <SkeletonChart />
        </div>
      )}
      {message && (
        <p style={{ textAlign: "center", color: "var(--color-text-muted)", fontSize: "0.875rem", marginTop: "1rem" }}>
          {message}
        </p>
      )}
    </div>
  );
}
