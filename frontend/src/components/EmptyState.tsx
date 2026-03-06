interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
}

export default function EmptyState({ title, description, icon }: EmptyStateProps) {
  return (
    <div
      style={{
        padding: "3rem 2rem",
        textAlign: "center",
        color: "var(--color-text-muted)",
      }}
    >
      {icon && (
        <div
          style={{
            width: 64,
            height: 64,
            margin: "0 auto 1rem",
            borderRadius: "var(--radius-md)",
            background: "var(--color-bg-elevated)",
            border: "1px dashed var(--color-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "2rem",
          }}
        >
          {icon}
        </div>
      )}
      <h3 style={{ margin: "0 0 0.5rem 0", fontSize: "1.125rem", fontWeight: 600, color: "var(--color-text-secondary)" }}>
        {title}
      </h3>
      {description && (
        <p style={{ margin: 0, fontSize: "0.875rem", maxWidth: 320, marginLeft: "auto", marginRight: "auto" }}>
          {description}
        </p>
      )}
    </div>
  );
}
