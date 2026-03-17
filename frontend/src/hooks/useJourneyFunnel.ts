import { useState, useEffect } from "react";
import { fetchFunnelJourney } from "../api/client";
import { useTenant } from "../contexts/TenantContext";
import type { JourneyFunnelResponse, DashboardFilters } from "../types/api";

interface UseJourneyFunnelResult {
  data: JourneyFunnelResponse | null;
  error: string | null;
  isLoading: boolean;
  refetch: () => void;
}

export function useJourneyFunnel(filters?: DashboardFilters): UseJourneyFunnelResult {
  const [data, setData] = useState<JourneyFunnelResponse | null>(null);
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
    fetchFunnelJourney(hotelId, {
      from: filters?.from,
      to: filters?.to,
    })
      .then(setData)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Erro ao carregar funil da jornada")
      )
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    load();
  }, [filters?.from, filters?.to]);

  return { data, error, isLoading, refetch: load };
}
