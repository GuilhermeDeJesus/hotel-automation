interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div
      className="card"
      style={{
        padding: "2rem",
        color: "var(--color-error)",
        textAlign: "center",
        maxWidth: 480,
        margin: "0 auto",
      }}
    >
      <p style={{ margin: "0 0 1rem 0", fontSize: "0.9375rem" }}>{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          style={{
            padding: "0.5rem 1.25rem",
            fontSize: "0.875rem",
            fontWeight: 500,
            background: "var(--color-error-muted)",
            border: "1px solid var(--color-error)",
            borderRadius: "var(--radius-sm)",
            color: "var(--color-error)",
            cursor: "pointer",
          }}
        >
          Tentar novamente
        </button>
      )}
    </div>
  );
}
