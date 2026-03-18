import { useState, useEffect, useRef } from "react";
import { fetchPayments } from "../api/client";
import { useTenant } from "../contexts/TenantContext";
import type { PaymentsResponse, PaymentsFilters } from "../types/api";

interface UsePaymentsResult {
  data: PaymentsResponse | null;
  error: string | null;
  isLoading: boolean;
  refetch: () => void;
}

export function usePayments(filters?: PaymentsFilters): UsePaymentsResult {
  const [data, setData] = useState<PaymentsResponse | null>(null);
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
    fetchPayments(hotelId, {
      reservation_id: filters?.reservation_id,
      status: filters?.status || undefined,
      limit: 100,
    })
      .then((res) => {
        if (requestId !== requestIdRef.current) return;
        setData(res);
      })
      .catch((e) => {
        if (requestId !== requestIdRef.current) return;
        setError(e instanceof Error ? e.message : "Erro ao carregar pagamentos");
      })
      .finally(() => {
        if (requestId !== requestIdRef.current) return;
        setIsLoading(false);
      });
  };

  useEffect(() => {
    load();
  }, [hotelId, filters?.reservation_id, filters?.status]);

  return { data, error, isLoading, refetch: load };
}
