import { useState, useEffect } from "react";
import { useHotelConfig } from "../hooks/useHotelConfig";
import { updateHotelConfig } from "../api/client";
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";
import { useToast } from "../contexts/ToastContext";

export default function HotelConfig() {
  const { data, error, isLoading, refetch } = useHotelConfig();
  const { showToast } = useToast();
  const [requiresPayment, setRequiresPayment] = useState(false);
  const [allowsWithoutPayment, setAllowsWithoutPayment] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      setRequiresPayment(data.requires_payment_for_confirmation);
      setAllowsWithoutPayment(data.allows_reservation_without_payment);
    }
  }, [data]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveError(null);
    setSaving(true);
    try {
      await updateHotelConfig({
        requires_payment_for_confirmation: requiresPayment,
        allows_reservation_without_payment: allowsWithoutPayment,
      });
      showToast("Configuração salva com sucesso.", "success");
      refetch();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro ao salvar";
      setSaveError(msg);
      showToast(msg, "error");
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div>
        <h1 className="page-title">Configuração do hotel</h1>
        <LoadingState variant="chart" message="Carregando configuração..." />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1 className="page-title">Configuração do hotel</h1>
        <ErrorState message={`Erro ao carregar configuração: ${error}`} onRetry={refetch} />
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div>
      <h1 className="page-title">Configuração do hotel</h1>
      <p
        style={{
          margin: "-0.75rem 0 1.5rem 0",
          color: "var(--color-text-muted)",
          fontSize: "0.9375rem",
        }}
      >
        Configure as regras de pagamento para reservas. O bot de WhatsApp usa essas configurações
        para oferecer ou não a opção de confirmar sem pagamento imediato.
      </p>
      <div className="card" style={{ padding: "1.5rem", maxWidth: 560 }}>
        <div style={{ marginBottom: "1rem", fontWeight: 600, fontSize: "1rem" }}>
          {data.name}
        </div>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "1.5rem" }}>
            <label
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "0.75rem",
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={requiresPayment}
                onChange={(e) => setRequiresPayment(e.target.checked)}
                style={{ marginTop: "0.25rem" }}
              />
              <div>
                <div style={{ fontWeight: 500, marginBottom: "0.25rem" }}>
                  Exigir pagamento para confirmação
                </div>
                <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                  Se ativo, a reserva só pode ser confirmada após pagamento aprovado. O bot não
                  oferece "Confirmar sem pagamento".
                </div>
              </div>
            </label>
          </div>
          <div style={{ marginBottom: "1.5rem" }}>
            <label
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "0.75rem",
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={allowsWithoutPayment}
                onChange={(e) => setAllowsWithoutPayment(e.target.checked)}
                style={{ marginTop: "0.25rem" }}
              />
              <div>
                <div style={{ fontWeight: 500, marginBottom: "0.25rem" }}>
                  Permitir reserva sem pagamento imediato
                </div>
                <div style={{ fontSize: "0.8125rem", color: "var(--color-text-muted)" }}>
                  Se ativo, o bot oferece as duas opções: "Pagar agora" e "Confirmar sem pagamento
                  imediato".
                </div>
              </div>
            </label>
          </div>
          {saveError && (
            <div
              style={{
                padding: "0.75rem 1rem",
                marginBottom: "1rem",
                background: "var(--color-error-muted)",
                borderRadius: "var(--radius-sm)",
                color: "var(--color-error)",
                fontSize: "0.875rem",
              }}
            >
              {saveError}
            </div>
          )}
          <button
            type="submit"
            disabled={saving}
            style={{
              padding: "0.5rem 1.25rem",
              fontSize: "0.875rem",
              fontWeight: 600,
              background: "var(--color-accent)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              color: "white",
              cursor: saving ? "not-allowed" : "pointer",
              opacity: saving ? 0.7 : 1,
            }}
          >
            {saving ? "Salvando..." : "Salvar configuração"}
          </button>
        </form>
      </div>
    </div>
  );
}
