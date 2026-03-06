import { useState, useEffect } from "react";
import { fetchLeads } from "../api/client";
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

  const load = () => {
    setIsLoading(true);
    setError(null);
    fetchLeads({
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
  }, [filters?.from, filters?.to, filters?.status]);

  return { data, error, isLoading, refetch: load };
}
