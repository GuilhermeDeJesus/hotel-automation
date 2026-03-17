import React, { createContext, useContext, useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";

type TenantContextValue = {
  hotelId: string | null;
  role: string | null;
  setHotelId: (hotelId: string | null) => void;
};

const TenantContext = createContext<TenantContextValue | undefined>(undefined);

type TenantProviderProps = {
  children: React.ReactNode;
};

function decodeToken(token: string | null): { hotel_id?: string; role?: string } | null {
  if (!token) return null;
  try {
    const [, payload] = token.split(".");
    if (!payload) return null;
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export const TenantProvider: React.FC<TenantProviderProps> = ({ children }) => {
  const params = useParams();
  const location = useLocation();
  const [hotelId, setHotelIdState] = useState<string | null>(() => {
    const hotelIdFromRoute = (params as { hotelId?: string }).hotelId || null;
    const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
    const payload = decodeToken(token);
    const hotelIdFromToken = (payload?.hotel_id as string | undefined) || null;
    const storedHotelId = typeof window !== "undefined" ? localStorage.getItem("selected_hotel_id") : null;
    return hotelIdFromRoute || hotelIdFromToken || storedHotelId;
  });
  const [role, setRole] = useState<string | null>(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
    const payload = decodeToken(token);
    return (payload?.role as string | undefined) || null;
  });

  useEffect(() => {
    const hotelIdFromRoute = (params as { hotelId?: string }).hotelId || null;
    const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
    const payload = decodeToken(token);
    const hotelIdFromToken = (payload?.hotel_id as string | undefined) || null;
    const storedHotelId = typeof window !== "undefined" ? localStorage.getItem("selected_hotel_id") : null;

    // Prioridade: rota > token > seleção manual
    setHotelIdState(hotelIdFromRoute || hotelIdFromToken || storedHotelId);
    setRole((payload?.role as string | undefined) || null);
  }, [location.pathname, params]);

  const setHotelId = (newHotelId: string | null) => {
    setHotelIdState(newHotelId);
    if (typeof window !== "undefined") {
      if (newHotelId) {
        localStorage.setItem("selected_hotel_id", newHotelId);
      } else {
        localStorage.removeItem("selected_hotel_id");
      }
    }
  };

  const value: TenantContextValue = { hotelId, role, setHotelId };

  return <TenantContext.Provider value={value}>{children}</TenantContext.Provider>;
};

export function useTenant(): TenantContextValue {
  const ctx = useContext(TenantContext);
  if (!ctx) {
    throw new Error("useTenant must be used within a TenantProvider");
  }
  return ctx;
}

