import { useState, useEffect } from "react";
import { fetchFunnel } from "../api/client";
import { useTenant } from "../contexts/TenantContext";
import type { FunnelResponse, DashboardFilters } from "../types/api";

interface UseFunnelResult {
  data: FunnelResponse | null;
  error: string | null;
  isLoading: boolean;
  refetch: () => void;
}

export function useFunnel(filters?: DashboardFilters): UseFunnelResult {
  const [data, setData] = useState<FunnelResponse | null>(null);
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
    fetchFunnel(hotelId, {
      from: filters?.from,
      to: filters?.to,
    })
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro ao carregar funil"))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    load();
  }, [filters?.from, filters?.to]);

  return { data, error, isLoading, refetch: load };
}
