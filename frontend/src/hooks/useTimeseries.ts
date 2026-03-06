import { useState, useEffect } from "react";
import { fetchTimeseries } from "../api/client";
import type { TimeseriesResponse, DashboardFilters } from "../types/api";

interface UseTimeseriesResult {
  data: TimeseriesResponse | null;
  error: string | null;
  isLoading: boolean;
  refetch: () => void;
}

export function useTimeseries(filters?: DashboardFilters): UseTimeseriesResult {
  const [data, setData] = useState<TimeseriesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const load = () => {
    setIsLoading(true);
    setError(null);
    fetchTimeseries({
      from: filters?.from,
      to: filters?.to,
      source: filters?.source || undefined,
      status: filters?.status || undefined,
      granularity: filters?.granularity || "day",
    })
      .then(setData)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Erro ao carregar série temporal")
      )
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    load();
  }, [filters?.from, filters?.to, filters?.source, filters?.status, filters?.granularity]);

  return { data, error, isLoading, refetch: load };
}
