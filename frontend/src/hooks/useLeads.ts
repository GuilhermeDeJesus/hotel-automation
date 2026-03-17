import { useState, useEffect } from "react";
import { fetchLeads } from "../api/client";
import { useTenant } from "../contexts/TenantContext";
import type { LeadsResponse, DashboardFilters } from "../types/api";

interface UseLeadsResult {
  data: LeadsResponse | null;
  error: string | null;
  isLoading: boolean;
  refetch: () => void;
}

export function useLeads(filters?: DashboardFilters): UseLeadsResult {
  const [data, setData] = useState<LeadsResponse | null>(null);
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
    fetchLeads(hotelId, {
      from: filters?.from,
      to: filters?.to,
      status: filters?.status || undefined,
    })
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro ao carregar leads"))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    load();
  }, [hotelId, filters?.from, filters?.to, filters?.status]);

  return { data, error, isLoading, refetch: load };
}
