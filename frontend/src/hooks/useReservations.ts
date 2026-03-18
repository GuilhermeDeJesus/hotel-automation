import { useState, useEffect, useRef } from "react";
import { fetchReservations } from "../api/client";
import { useTenant } from "../contexts/TenantContext";
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

  const { hotelId } = useTenant();
  const requestIdRef = useRef(0);

  const load = () => {
    const requestId = ++requestIdRef.current;

    if (!hotelId) {
      setError("Hotel não definido. Faça login novamente.");
      setData(null);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    fetchReservations(hotelId, {
      from: filters?.from,
      to: filters?.to,
      status: filters?.status || undefined,
      room_number: filters?.room_number || undefined,
      limit: 100,
    })
      .then((res) => {
        if (requestId !== requestIdRef.current) return;
        setData(res);
      })
      .catch((e) => {
        if (requestId !== requestIdRef.current) return;
        setError(e instanceof Error ? e.message : "Erro ao carregar reservas");
      })
      .finally(() => {
        if (requestId !== requestIdRef.current) return;
        setIsLoading(false);
      });
  };

  useEffect(() => {
    load();
  }, [hotelId, filters?.from, filters?.to, filters?.status, filters?.room_number]);

  return { data, error, isLoading, refetch: load };
}
