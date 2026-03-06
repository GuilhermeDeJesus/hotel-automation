import { useState, useEffect } from "react";
import { fetchKpisCompare } from "../api/client";
import type { KpisCompareResponse, DashboardFilters } from "../types/api";

interface UseKpisCompareResult {
  data: KpisCompareResponse | null;
  error: string | null;
  isLoading: boolean;
  refetch: () => void;
}

export function useKpisCompare(filters?: DashboardFilters): UseKpisCompareResult {
  const [data, setData] = useState<KpisCompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const load = () => {
    setIsLoading(true);
    setError(null);
    fetchKpisCompare({
      from: filters?.from,
      to: filters?.to,
      source: filters?.source || undefined,
      status: filters?.status || undefined,
      granularity: filters?.granularity || "day",
    })
      .then(setData)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Erro ao carregar comparação")
      )
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    load();
  }, [filters?.from, filters?.to, filters?.source, filters?.status, filters?.granularity]);

  return { data, error, isLoading, refetch: load };
}
