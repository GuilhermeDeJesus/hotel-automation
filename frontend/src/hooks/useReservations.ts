import { useState, useEffect } from "react";
import { fetchReservations } from "../api/client";
import type { ReservationsResponse, ReservationsFilters } from "../types/api";

interface UseReservationsResult {
  data: ReservationsResponse | null;
  error: string | null;
  isLoading: boolean;
  refetch: () => void;
}

export function useReservations(filters?: ReservationsFilters): UseReservationsResult {
  const [data, setData] = useState<ReservationsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const load = () => {
    setIsLoading(true);
    setError(null);
    fetchReservations({
      from: filters?.from,
      to: filters?.to,
      status: filters?.status || undefined,
      room_number: filters?.room_number || undefined,
      limit: 100,
    })
      .then(setData)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Erro ao carregar reservas")
      )
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    load();
  }, [filters?.from, filters?.to, filters?.status, filters?.room_number]);

  return { data, error, isLoading, refetch: load };
}
