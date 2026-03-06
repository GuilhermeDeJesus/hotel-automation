import { useState, useEffect } from "react";
import { useAuditEvents } from "../hooks/useAuditEvents";
import { getAdminToken, setAdminToken } from "../api/client";
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";

function defaultDateRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 6);
  return {
    from: start.toISOString().slice(0, 10),
    to: end.toISOString().slice(0, 10),
  };
}

export default function AdminAudit() {
  const [tokenInput, setTokenInput] = useState("");
  const [hasToken, setHasToken] = useState(false);
  const [filters, setFilters] = useState({
    from: defaultDateRange().from,
    to: defaultDateRange().to,
    outcome: "",
    page: 1,
    page_size: 20,
  });
  const { data, error, isLoading, refetch } = useAuditEvents(filters, hasToken);

  useEffect(() => {
    setHasToken(!!getAdminToken());
  }, []);

  const handleTokenSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (tokenInput.trim()) {
      setAdminToken(tokenInput.trim());
      setHasToken(true);
      setTokenInput("");
      refetch();
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem("saas_admin_token");
    setHasToken(false);
  };

  if (!hasToken) {
    return (
      <div>
        <h1 className="page-title">Auditoria (Admin)</h1>
        <p
          style={{
            margin: "-0.75rem 0 1.5rem 0",
            color: "var(--color-text-muted)",
            fontSize: "0.9375rem",
          }}
        >
          Esta página requer autenticação. Informe o token de administrador configurado em
          SAAS_ADMIN_TOKEN.
        </p>
        <div className="card" style={{ padding: "1.5rem", maxWidth: 400 }}>
          <form onSubmit={handleTokenSubmit}>
            <label style={{ display: "block", marginBottom: "0.5rem", fontWeight: 500 }}>
              Token admin
            </label>
            <input
              type="password"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="Informe o token"
              style={{
                width: "100%",
                padding: "0.5rem 0.875rem",
                marginBottom: "1rem",
                background: "var(--color-bg-elevated)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                color: "var(--color-text)",
                fontSize: "0.875rem",
              }}
            />
            <button
              type="submit"
              disabled={!tokenInput.trim()}
              style={{
                padding: "0.5rem 1rem",
                fontSize: "0.875rem",
                fontWeight: 600,
                background: "var(--color-accent)",
                border: "none",
                borderRadius: "var(--radius-sm)",
                color: "white",
                cursor: tokenInput.trim() ? "pointer" : "not-allowed",
                opacity: tokenInput.trim() ? 1 : 0.6,
              }}
            >
              Acessar
            </button>
          </form>
        </div>
      </div>
    );
  }

  const pagination = data?.pagination;
  const totalPages = pagination
    ? Math.ceil(pagination.total / pagination.page_size)
    : 0;

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "1rem",
          marginBottom: "1.5rem",
        }}
      >
        <div>
          <h1 className="page-title" style={{ marginBottom: "0.25rem" }}>
            Auditoria (Admin)
          </h1>
          <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "0.9375rem" }}>
            Eventos de auditoria: cache invalidate, operações administrativas.
          </p>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          style={{
            padding: "0.375rem 0.75rem",
            fontSize: "0.8125rem",
            background: "transparent",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            color: "var(--color-text-muted)",
            cursor: "pointer",
          }}
        >
          Sair
        </button>
      </div>

      <div
        className="card"
        style={{
          padding: "1rem 1.25rem",
          marginBottom: "1.5rem",
          display: "flex",
          flexWrap: "wrap",
          gap: "1rem",
          alignItems: "center",
        }}
      >
        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>De</span>
          <input
            type="date"
            value={filters.from}
            onChange={(e) => setFilters((f) => ({ ...f, from: e.target.value, page: 1 }))}
            style={{
              padding: "0.5rem 0.875rem",
              background: "var(--color-bg-elevated)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              color: "var(--color-text)",
              fontSize: "0.875rem",
            }}
          />
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>Até</span>
          <input
            type="date"
            value={filters.to}
            onChange={(e) => setFilters((f) => ({ ...f, to: e.target.value, page: 1 }))}
            style={{
              padding: "0.5rem 0.875rem",
              background: "var(--color-bg-elevated)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              color: "var(--color-text)",
              fontSize: "0.875rem",
            }}
          />
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <span style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>Outcome</span>
          <select
            value={filters.outcome}
            onChange={(e) =>
              setFilters((f) => ({ ...f, outcome: e.target.value, page: 1 }))
            }
            style={{
              padding: "0.5rem 0.875rem",
              background: "var(--color-bg-elevated)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              color: "var(--color-text)",
              fontSize: "0.875rem",
              minWidth: 120,
            }}
          >
            <option value="">Todos</option>
            <option value="success">success</option>
            <option value="rate_limited">rate_limited</option>
          </select>
        </label>
      </div>

      {isLoading && <LoadingState variant="table" message="Carregando eventos..." />}

      {error && <ErrorState message={error} onRetry={refetch} />}

      {!isLoading && !error && data && (
        <>
          <div className="card" style={{ overflow: "hidden", marginBottom: "1rem" }}>
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
                      }}
                    >
                      Data
                    </th>
                    <th
                      style={{
                        textAlign: "left",
                        padding: "1rem 1.25rem",
                        color: "var(--color-text-muted)",
                        fontWeight: 600,
                        fontSize: "0.75rem",
                        textTransform: "uppercase",
                      }}
                    >
                      Tipo
                    </th>
                    <th
                      style={{
                        textAlign: "left",
                        padding: "1rem 1.25rem",
                        color: "var(--color-text-muted)",
                        fontWeight: 600,
                        fontSize: "0.75rem",
                        textTransform: "uppercase",
                      }}
                    >
                      IP
                    </th>
                    <th
                      style={{
                        textAlign: "left",
                        padding: "1rem 1.25rem",
                        color: "var(--color-text-muted)",
                        fontWeight: 600,
                        fontSize: "0.75rem",
                        textTransform: "uppercase",
                      }}
                    >
                      Outcome
                    </th>
                    <th
                      style={{
                        textAlign: "left",
                        padding: "1rem 1.25rem",
                        color: "var(--color-text-muted)",
                        fontWeight: 600,
                        fontSize: "0.75rem",
                        textTransform: "uppercase",
                      }}
                    >
                      Detalhes
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.length === 0 ? (
                    <tr>
                      <td
                        colSpan={5}
                        style={{
                          padding: "2rem",
                          textAlign: "center",
                          color: "var(--color-text-muted)",
                        }}
                      >
                        Nenhum evento no período
                      </td>
                    </tr>
                  ) : (
                    data.items.map((evt, i) => (
                      <tr
                        key={evt.id}
                        style={{
                          borderBottom: "1px solid var(--color-border)",
                          background: i % 2 === 1 ? "rgba(255,255,255,0.02)" : "transparent",
                        }}
                      >
                        <td
                          style={{
                            padding: "1rem 1.25rem",
                            color: "var(--color-text-muted)",
                            fontSize: "0.8125rem",
                          }}
                        >
                          {evt.created_at
                            ? new Date(evt.created_at).toLocaleString("pt-BR")
                            : "—"}
                        </td>
                        <td style={{ padding: "1rem 1.25rem" }}>{evt.event_type}</td>
                        <td style={{ padding: "1rem 1.25rem", fontFamily: "monospace" }}>
                          {evt.client_ip}
                        </td>
                        <td style={{ padding: "1rem 1.25rem" }}>{evt.outcome}</td>
                        <td
                          style={{
                            padding: "1rem 1.25rem",
                            fontSize: "0.8125rem",
                            color: "var(--color-text-muted)",
                          }}
                        >
                          {evt.deleted_keys != null && `keys: ${evt.deleted_keys}`}
                          {evt.retry_after != null && ` retry: ${evt.retry_after}s`}
                          {evt.reason && ` ${evt.reason}`}
                          {!evt.deleted_keys && !evt.retry_after && !evt.reason && "—"}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {totalPages > 1 && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                marginTop: "1rem",
              }}
            >
              <button
                type="button"
                onClick={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}
                disabled={filters.page <= 1}
                style={{
                  padding: "0.375rem 0.75rem",
                  fontSize: "0.875rem",
                  background: "var(--color-bg-elevated)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--color-text)",
                  cursor: filters.page <= 1 ? "not-allowed" : "pointer",
                  opacity: filters.page <= 1 ? 0.5 : 1,
                }}
              >
                Anterior
              </button>
              <span style={{ fontSize: "0.875rem", color: "var(--color-text-muted)" }}>
                Página {filters.page} de {totalPages} ({pagination?.total ?? 0} eventos)
              </span>
              <button
                type="button"
                onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}
                disabled={filters.page >= totalPages}
                style={{
                  padding: "0.375rem 0.75rem",
                  fontSize: "0.875rem",
                  background: "var(--color-bg-elevated)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--color-text)",
                  cursor: filters.page >= totalPages ? "not-allowed" : "pointer",
                  opacity: filters.page >= totalPages ? 0.5 : 1,
                }}
              >
                Próxima
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
