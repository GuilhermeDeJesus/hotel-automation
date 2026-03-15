const baseUrl = import.meta.env.VITE_API_BASE_URL || "/api";

async function fetchApi<T>(
  path: string,
  params?: Record<string, string | undefined>,
  headers?: Record<string, string>
): Promise<T> {
  const search = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") {
        search.set(k, v);
      }
    });
  }
  const query = search.toString();
  const url = `${baseUrl}${path}${query ? `?${query}` : ""}`;
  const res = await fetch(url, { headers: headers ?? {} });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

/** Obtém o token admin (env ou sessionStorage). */
export function getAdminToken(): string | null {
  const fromEnv = import.meta.env.VITE_SAAS_ADMIN_TOKEN;
  if (fromEnv) return fromEnv;
  return sessionStorage.getItem("saas_admin_token");
}

/** Salva o token admin na sessão. */
export function setAdminToken(token: string): void {
  sessionStorage.setItem("saas_admin_token", token);
}

export async function fetchKpis(params?: {
  from?: string;
  to?: string;
  source?: string;
  status?: string;
  granularity?: string;
}) {
  return fetchApi<import("../types/api").KpisResponse>("/saas/kpis", params);
}

export async function fetchLeads(params?: {
  from?: string;
  to?: string;
  status?: string;
}) {
  return fetchApi<import("../types/api").LeadsResponse>("/saas/leads", params);
}

export async function fetchFunnelJourney(params?: {
  from?: string;
  to?: string;
}) {
  return fetchApi<import("../types/api").JourneyFunnelResponse>("/saas/funnel/journey", params);
}

export async function fetchFunnel(params?: {
  from?: string;
  to?: string;
}) {
  return fetchApi<import("../types/api").FunnelResponse>("/saas/funnel", params);
}

export async function fetchTimeseries(params?: {
  from?: string;
  to?: string;
  source?: string;
  status?: string;
  granularity?: string;
}) {
  return fetchApi<import("../types/api").TimeseriesResponse>("/saas/timeseries", params);
}

export async function fetchKpisCompare(params?: {
  from?: string;
  to?: string;
  source?: string;
  status?: string;
  granularity?: string;
}) {
  return fetchApi<import("../types/api").KpisCompareResponse>("/saas/kpis/compare", params);
}

export async function fetchReservations(params?: {
  from?: string;
  to?: string;
  status?: string;
  room_number?: string;
  limit?: number;
}) {
  const p: Record<string, string | undefined> = {};
  if (params) {
    if (params.from) p.from = params.from;
    if (params.to) p.to = params.to;
    if (params.status) p.status = params.status;
    if (params.room_number) p.room_number = params.room_number;
    if (params.limit) p.limit = String(params.limit);
  }
  return fetchApi<import("../types/api").ReservationsResponse>("/saas/reservations", p);
}

export async function markReservationNoShow(reservationId: string) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "/api";
  const res = await fetch(`${baseUrl}/saas/reservations/${reservationId}/mark-no-show`, {
    method: "POST",
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function fetchPayments(params?: {
  reservation_id?: string;
  status?: string;
  limit?: number;
}) {
  const p: Record<string, string | undefined> = {};
  if (params) {
    if (params.reservation_id) p.reservation_id = params.reservation_id;
    if (params.status) p.status = params.status;
    if (params.limit) p.limit = String(params.limit);
  }
  return fetchApi<import("../types/api").PaymentsResponse>("/saas/payments", p);
}

export async function fetchHotelConfig() {
  return fetchApi<import("../types/api").HotelConfig>("/saas/hotel/config");
}

export async function fetchAuditEvents(params?: {
  from?: string;
  to?: string;
  outcome?: string;
  page?: number;
  page_size?: number;
}): Promise<import("../types/api").AuditEventsResponse> {
  const token = getAdminToken();
  if (!token) {
    throw new Error("Token admin não configurado. Informe o token na página de auditoria.");
  }
  const p: Record<string, string | undefined> = {};
  if (params) {
    if (params.from) p.from = params.from;
    if (params.to) p.to = params.to;
    if (params.outcome) p.outcome = params.outcome;
    if (params.page) p.page = String(params.page);
    if (params.page_size) p.page_size = String(params.page_size);
  }
  return fetchApi<import("../types/api").AuditEventsResponse>("/saas/audit-events", p, {
    "X-Admin-Token": token,
  });
}

export async function fetchRooms() {
  return fetchApi<{ items: import("../types/api").Room[] }>("/saas/rooms");
}

export async function createRoom(payload: {
  number: string;
  room_type: string;
  daily_rate: number;
  max_guests: number;
}) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "/api";
  const res = await fetch(`${baseUrl}/saas/rooms`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function updateRoom(
  roomNumber: string,
  payload: { room_type?: string; daily_rate?: number; max_guests?: number; status?: string }
) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "/api";
  const res = await fetch(`${baseUrl}/saas/rooms/${encodeURIComponent(roomNumber)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function deleteRoom(roomNumber: string) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "/api";
  const res = await fetch(`${baseUrl}/saas/rooms/${encodeURIComponent(roomNumber)}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function updateHotelConfig(payload: {
  name?: string;
  address?: string;
  contact_phone?: string;
  checkin_time?: string;
  checkout_time?: string;
  cancellation_policy?: string;
  pet_policy?: string;
  child_policy?: string;
  amenities?: string;
  requires_payment_for_confirmation?: boolean;
  allows_reservation_without_payment?: boolean;
}) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "/api";
  const res = await fetch(`${baseUrl}/saas/hotel/config`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function invalidateCache(): Promise<{ deleted_keys: number }> {
  const token = getAdminToken();
  if (!token) {
    throw new Error("Token admin não configurado. Acesse Auditoria para configurar.");
  }
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "/api";
  const res = await fetch(`${baseUrl}/saas/cache/invalidate`, {
    method: "POST",
    headers: { "X-Admin-Token": token },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
    if (res.status === 429) {
      throw new Error("Limite de requisições excedido. Tente novamente em alguns segundos.");
    }
    throw new Error(detail || `Erro: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function confirmPaymentManual(paymentId: string, transactionId?: string) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "/api";
  const url = new URL(`${baseUrl}/saas/payments/${paymentId}/confirm`);
  if (transactionId) url.searchParams.set("transaction_id", transactionId);
  const res = await fetch(url.toString(), { method: "POST" });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
