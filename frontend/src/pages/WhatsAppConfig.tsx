import { useState, useEffect } from "react";
import { useTenant } from "../contexts/TenantContext";
import { hotelConfigApi } from "../api/hotelConfig";
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";
import { useToast } from "../contexts/ToastContext";

export default function WhatsAppConfig() {
  const { hotelId } = useTenant();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [whatsappEnabled, setWhatsappEnabled] = useState(true);
  const [whatsappNumber, setWhatsappNumber] = useState("");
  const [businessHoursStart, setBusinessHoursStart] = useState("08:00");
  const [businessHoursEnd, setBusinessHoursEnd] = useState("22:00");

  const load = async () => {
    if (!hotelId) {
      setError("Hotel não definido. Faça login novamente.");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const config = await hotelConfigApi.getHotelConfig(hotelId);
      setWhatsappEnabled(config.whatsapp_enabled ?? true);
      setWhatsappNumber(config.whatsapp_number ?? "");
      setBusinessHoursStart(config.whatsapp_business_hours?.start ?? "08:00");
      setBusinessHoursEnd(config.whatsapp_business_hours?.end ?? "22:00");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar configuração");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [hotelId]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hotelId) return;
    setSaving(true);
    try {
      await hotelConfigApi.updateHotelConfig(hotelId, {
        whatsapp_enabled: whatsappEnabled,
        whatsapp_number: whatsappEnabled ? whatsappNumber : undefined,
        whatsapp_business_hours: whatsappEnabled
          ? { start: businessHoursStart, end: businessHoursEnd }
          : undefined,
      });
      showToast("Configuração do WhatsApp salva com sucesso.", "success");
    } catch (e) {
      showToast(
        e instanceof Error ? e.message : "Erro ao salvar configuração",
        "error"
      );
    } finally {
      setSaving(false);
    }
  };

  if (!hotelId) {
    return (
      <div>
        <h1 className="page-title">WhatsApp - Atendimento por IA</h1>
        <ErrorState message="Hotel não definido. Faça login novamente." onRetry={load} />
      </div>
    );
  }

  if (loading) {
    return (
      <div>
        <h1 className="page-title">WhatsApp - Atendimento por IA</h1>
        <LoadingState variant="chart" message="Carregando configuração..." />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1 className="page-title">WhatsApp - Atendimento por IA</h1>
        <ErrorState message={`Erro ao carregar: ${error}`} onRetry={load} />
      </div>
    );
  }

  return (
    <div>
      <h1 className="page-title">WhatsApp - Atendimento por IA</h1>
      <p
        style={{
          margin: "-0.75rem 0 1.5rem 0",
          color: "var(--color-text-muted)",
          fontSize: "0.9375rem",
        }}
      >
        Configure o número de WhatsApp que receberá as mensagens dos hóspedes. O bot de IA
        responderá automaticamente neste número. O webhook (Meta ou Twilio) deve apontar para
        este número.
      </p>

      <form onSubmit={handleSave}>
        <div className="card" style={{ padding: "1.5rem", maxWidth: 480 }}>
          <div style={{ marginBottom: "1.5rem" }}>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={whatsappEnabled}
                onChange={(e) => setWhatsappEnabled(e.target.checked)}
                style={{ width: 18, height: 18 }}
              />
              <span style={{ fontWeight: 500 }}>Atendimento por WhatsApp habilitado</span>
            </label>
          </div>

          {whatsappEnabled && (
            <>
              <div style={{ marginBottom: "1rem" }}>
                <label
                  style={{
                    display: "block",
                    fontWeight: 500,
                    marginBottom: "0.375rem",
                    fontSize: "0.875rem",
                  }}
                >
                  Número do WhatsApp (formato internacional)
                </label>
                <input
                  type="tel"
                  value={whatsappNumber}
                  onChange={(e) => setWhatsappNumber(e.target.value)}
                  placeholder="+5521999999999"
                  style={{
                    width: "100%",
                    padding: "0.5rem 0.75rem",
                    fontSize: "0.875rem",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-sm)",
                    background: "var(--color-bg)",
                    color: "var(--color-text)",
                  }}
                />
                <div
                  style={{
                    fontSize: "0.8125rem",
                    color: "var(--color-text-muted)",
                    marginTop: "0.25rem",
                  }}
                >
                  Ex: +5521999999999 (código do país + DDD + número)
                </div>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "1rem",
                  marginBottom: "1rem",
                }}
              >
                <div>
                  <label
                    style={{
                      display: "block",
                      fontWeight: 500,
                      marginBottom: "0.375rem",
                      fontSize: "0.875rem",
                    }}
                  >
                    Horário de início
                  </label>
                  <input
                    type="time"
                    value={businessHoursStart}
                    onChange={(e) => setBusinessHoursStart(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "0.5rem 0.75rem",
                      fontSize: "0.875rem",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-sm)",
                      background: "var(--color-bg)",
                      color: "var(--color-text)",
                    }}
                  />
                </div>
                <div>
                  <label
                    style={{
                      display: "block",
                      fontWeight: 500,
                      marginBottom: "0.375rem",
                      fontSize: "0.875rem",
                    }}
                  >
                    Horário de término
                  </label>
                  <input
                    type="time"
                    value={businessHoursEnd}
                    onChange={(e) => setBusinessHoursEnd(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "0.5rem 0.75rem",
                      fontSize: "0.875rem",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-sm)",
                      background: "var(--color-bg)",
                      color: "var(--color-text)",
                    }}
                  />
                </div>
              </div>
            </>
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
        </div>
      </form>
    </div>
  );
}
