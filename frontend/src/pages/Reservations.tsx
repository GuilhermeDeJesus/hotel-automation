import { useState } from "react";
import { useReservations } from "../hooks/useReservations";
import ReservationsFilters from "../components/ReservationsFilters";
import ReservationsTable from "../components/ReservationsTable";
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";
import EmptyState from "../components/EmptyState";
import { IconInbox } from "../components/Icons";
import { markReservationNoShow } from "../api/client";
import { useTenant } from "../contexts/TenantContext";
import type { ReservationsFilters as ReservationsFiltersType } from "../types/api";

function defaultFilters(): ReservationsFiltersType {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 29);
  return {
    from: start.toISOString().slice(0, 10),
    to: end.toISOString().slice(0, 10),
  };
}

export default function Reservations() {
  const [filters, setFilters] = useState<ReservationsFiltersType>(defaultFilters);
  const { data, error, isLoading, refetch } = useReservations(filters);
  const { hotelId } = useTenant();
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const handleMarkNoShow = async (id: string) => {
    if (!hotelId) {
      setActionError("Hotel não definido. Faça login novamente.");
      return;
    }
    setActionError(null);
    setActionLoading(id);
    try {
      await markReservationNoShow(hotelId, id);
      refetch();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Erro ao marcar no-show");
    } finally {
      setActionLoading(null);
    }
  };

  if (isLoading) {
    return (
      <div>
        <h1 className="page-title">Reservas</h1>
        <LoadingState variant="table" message="Carregando reservas..." />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1 className="page-title">Reservas</h1>
        <ErrorState message={`Erro ao carregar reservas: ${error}`} onRetry={refetch} />
      </div>
    );
  }

  const reservations = data?.items ?? [];

  return (
    <div>
      <h1 className="page-title">Reservas</h1>
      <p
        style={{
          margin: "-0.75rem 0 1.5rem 0",
          color: "var(--color-text-muted)",
          fontSize: "0.9375rem",
        }}
      >
        Lista de reservas com filtros por período, status e quarto. Marque como no-show quando o
        hóspede não comparecer.
      </p>
      <ReservationsFilters filters={filters} onChange={setFilters} />
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
      {reservations.length === 0 ? (
        <div className="card">
          <EmptyState
            title="Nenhuma reserva encontrada"
            description="Não há reservas no período selecionado. Tente ajustar os filtros."
            icon={<IconInbox />}
          />
        </div>
      ) : (
        <ReservationsTable
          reservations={reservations}
          onMarkNoShow={handleMarkNoShow}
          markNoShowLoadingId={actionLoading}
        />
      )}
    </div>
  );
}
