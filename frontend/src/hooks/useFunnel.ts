import { useState, useEffect, useRef } from "react";
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
    fetchFunnel(hotelId, {
      from: filters?.from,
      to: filters?.to,
    })
      .then((res) => {
        if (requestId !== requestIdRef.current) return;
        setData(res);
      })
      .catch((e) => {
        if (requestId !== requestIdRef.current) return;
        setError(e instanceof Error ? e.message : "Erro ao carregar funil");
      })
      .finally(() => {
        if (requestId !== requestIdRef.current) return;
        setIsLoading(false);
      });
  };

  useEffect(() => {
    load();
  }, [hotelId, filters?.from, filters?.to]);

  return { data, error, isLoading, refetch: load };
}
