import { useState, useEffect } from "react";
import { fetchRooms } from "../api/client";
import type { Room } from "../types/api";

interface UseRoomsResult {
  data: Room[];
  error: string | null;
  isLoading: boolean;
  refetch: () => void;
}

export function useRooms(): UseRoomsResult {
  const [data, setData] = useState<Room[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const load = () => {
    setIsLoading(true);
    setError(null);
    fetchRooms()
      .then((res) => setData(res.items || []))
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Erro ao carregar quartos")
      )
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  return { data, error, isLoading, refetch: load };
}
