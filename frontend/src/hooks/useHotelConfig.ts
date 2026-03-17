import { useState, useEffect } from "react";
import { fetchHotelConfig } from "../api/client";
import { useTenant } from "../contexts/TenantContext";
import type { HotelConfig } from "../types/api";

interface UseHotelConfigResult {
  data: HotelConfig | null;
  error: string | null;
  isLoading: boolean;
  refetch: () => void;
}

export function useHotelConfig(): UseHotelConfigResult {
  const { hotelId } = useTenant();
  const [data, setData] = useState<HotelConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const load = () => {
    if (!hotelId) {
      setError("Hotel não definido. Faça login novamente.");
      setData(null);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    fetchHotelConfig(hotelId)
      .then(setData)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Erro ao carregar configuração")
      )
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    load();
  }, [hotelId]);

  return { data, error, isLoading, refetch: load };
}
