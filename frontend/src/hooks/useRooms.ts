import { useState, useEffect, useRef } from "react";
import { fetchRooms } from "../api/client";
import { useTenant } from "../contexts/TenantContext";
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

  const { hotelId } = useTenant();
  const requestIdRef = useRef(0);

  const load = () => {
    const requestId = ++requestIdRef.current;

    if (!hotelId) {
      setError("Hotel não definido. Faça login novamente.");
      setData([]);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    fetchRooms(hotelId)
      .then((res) => {
        if (requestId !== requestIdRef.current) return;
        setData(res.items || []);
      })
      .catch((e) => {
        if (requestId !== requestIdRef.current) return;
        setError(e instanceof Error ? e.message : "Erro ao carregar quartos");
      })
      .finally(() => {
        if (requestId !== requestIdRef.current) return;
        setIsLoading(false);
      });
  };

  useEffect(() => {
    load();
  }, [hotelId]);

  return { data, error, isLoading, refetch: load };
}
