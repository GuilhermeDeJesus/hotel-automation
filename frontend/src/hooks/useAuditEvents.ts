import { useState, useEffect } from "react";
import { fetchAuditEvents } from "../api/client";
import type { AuditEventsResponse } from "../types/api";

interface AuditEventsFilters {
  from?: string;
  to?: string;
  outcome?: string;
  page?: number;
  page_size?: number;
}

interface UseAuditEventsResult {
  data: AuditEventsResponse | null;
  error: string | null;
  isLoading: boolean;
  refetch: () => void;
}

export function useAuditEvents(
  filters?: AuditEventsFilters,
  enabled: boolean = true
): UseAuditEventsResult {
  const [data, setData] = useState<AuditEventsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const load = () => {
    if (!enabled) return;
    setIsLoading(true);
    setError(null);
    fetchAuditEvents({
      from: filters?.from,
      to: filters?.to,
      outcome: filters?.outcome,
      page: filters?.page ?? 1,
      page_size: filters?.page_size ?? 20,
    })
      .then(setData)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Erro ao carregar eventos de auditoria")
      )
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    if (enabled) {
      load();
    } else {
      setIsLoading(false);
      setError(null);
      setData(null);
    }
  }, [enabled, filters?.from, filters?.to, filters?.outcome, filters?.page, filters?.page_size]);

  return { data, error, isLoading, refetch: load };
}
