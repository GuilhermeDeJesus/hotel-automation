import { useState } from "react";
import { usePayments } from "../hooks/usePayments";
import PaymentsFilters from "../components/PaymentsFilters";
import PaymentsTable from "../components/PaymentsTable";
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";
import EmptyState from "../components/EmptyState";
import { IconInbox } from "../components/Icons";
import { confirmPaymentManual } from "../api/client";
import { useTenant } from "../contexts/TenantContext";
import type { PaymentsFilters as PaymentsFiltersType } from "../types/api";

export default function Payments() {
  const [filters, setFilters] = useState<PaymentsFiltersType>({});
  const { data, error, isLoading, refetch } = usePayments(filters);
  const { hotelId } = useTenant();
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const handleConfirm = async (id: string) => {
    if (!hotelId) {
      setActionError("Hotel não definido. Faça login novamente.");
      return;
    }
    setActionError(null);
    setActionLoading(id);
    try {
      await confirmPaymentManual(id);
      refetch();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Erro ao confirmar pagamento");
    } finally {
      setActionLoading(null);
    }
  };

  if (isLoading) {
    return (
      <div>
        <h1 className="page-title">Pagamentos</h1>
        <LoadingState variant="table" message="Carregando pagamentos..." />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1 className="page-title">Pagamentos</h1>
        <ErrorState message={`Erro ao carregar pagamentos: ${error}`} onRetry={refetch} />
      </div>
    );
  }

  const payments = data?.items ?? [];

  return (
    <div>
      <h1 className="page-title">Pagamentos</h1>
      <p
        style={{
          margin: "-0.75rem 0 1.5rem 0",
          color: "var(--color-text-muted)",
          fontSize: "0.9375rem",
        }}
      >
        Lista de pagamentos com filtro por reserva e status. Confirme manualmente quando o
        comprovante for recebido (Fase 0).
      </p>
      <PaymentsFilters filters={filters} onChange={setFilters} />
      {actionError && (
        <div
          className="card"
          style={{
            padding: "1rem 1.25rem",
            marginBottom: "1rem",
            background: "var(--color-error-muted)",
            borderColor: "var(--color-error)",
            color: "var(--color-error)",
          }}
        >
          {actionError}
        </div>
      )}
      {payments.length === 0 ? (
        <div className="card">
          <EmptyState
            title="Nenhum pagamento encontrado"
            description="Não há pagamentos com os filtros selecionados."
            icon={<IconInbox />}
          />
        </div>
      ) : (
        <PaymentsTable
          payments={payments}
          onConfirm={handleConfirm}
          confirmLoadingId={actionLoading}
        />
      )}
    </div>
  );
}
