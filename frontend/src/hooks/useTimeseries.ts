import { useState, useEffect, useRef } from "react";
import { fetchTimeseries } from "../api/client";
import { useTenant } from "../contexts/TenantContext";
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
    fetchTimeseries(hotelId, {
      from: filters?.from,
      to: filters?.to,
      source: filters?.source || undefined,
      status: filters?.status || undefined,
      granularity: filters?.granularity || "day",
    })
      .then((res) => {
        if (requestId !== requestIdRef.current) return;
        setData(res);
      })
      .catch((e) => {
        if (requestId !== requestIdRef.current) return;
        setError(
          e instanceof Error ? e.message : "Erro ao carregar série temporal"
        );
      })
      .finally(() => {
        if (requestId !== requestIdRef.current) return;
        setIsLoading(false);
      });
  };

  useEffect(() => {
    load();
  }, [hotelId, filters?.from, filters?.to, filters?.source, filters?.status, filters?.granularity]);

  return { data, error, isLoading, refetch: load };
}
