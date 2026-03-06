import { useState, useEffect } from "react";
import { fetchHotelConfig } from "../api/client";
import type { HotelConfig } from "../types/api";

interface UseHotelConfigResult {
  data: HotelConfig | null;
  error: string | null;
  isLoading: boolean;
  refetch: () => void;
}

export function useHotelConfig(): UseHotelConfigResult {
  const [data, setData] = useState<HotelConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const load = () => {
    setIsLoading(true);
    setError(null);
    fetchHotelConfig()
      .then(setData)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Erro ao carregar configuração")
      )
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  return { data, error, isLoading, refetch: load };
}
