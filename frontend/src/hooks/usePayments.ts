import { useState, useEffect } from "react";
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

  const load = () => {
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
      .then(setData)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Erro ao carregar pagamentos")
      )
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    load();
  }, [filters?.reservation_id, filters?.status]);

  return { data, error, isLoading, refetch: load };
}
