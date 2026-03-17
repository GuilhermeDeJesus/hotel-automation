import { useState, useEffect } from "react";
import { fetchKpis } from "../api/client";
import { useTenant } from "../contexts/TenantContext";
import type { KpisResponse, DashboardFilters } from "../types/api";

interface UseKpisResult {
  data: KpisResponse | null;
  error: string | null;
  isLoading: boolean;
  refetch: () => void;
}

export function useKpis(filters?: DashboardFilters): UseKpisResult {
  const [data, setData] = useState<KpisResponse | null>(null);
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
    fetchKpis(hotelId, {
      from: filters?.from,
      to: filters?.to,
      source: filters?.source || undefined,
      status: filters?.status || undefined,
      granularity: "day",
    })
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro ao carregar KPIs"))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    load();
    // Recarrega quando filtros OU hotelId mudam (ex.: superadmin seleciona hotel)
  }, [hotelId, filters?.from, filters?.to, filters?.source, filters?.status]);

  return { data, error, isLoading, refetch: load };
}
