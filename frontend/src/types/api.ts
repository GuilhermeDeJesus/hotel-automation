export interface KpisResponse {
  leads_captured: number;
  ai_response_rate: number;
  reservation_confirmation_rate: number;
  checkins_completed: number;
  avg_response_time_seconds: number;
  conversion_by_source: Record<string, number>;
  period: {
    from: string;
    to: string;
    source?: string;
    status?: string;
  };
  series?: SeriesPoint[];
  daily_series?: SeriesPoint[];
  granularity?: string;
}

export interface SeriesPoint {
  date: string;
  leads: number;
  inbound_messages: number;
  outbound_messages: number;
  confirmed_reservations: number;
  checkins: number;
  avg_response_time_seconds: number;
}

export interface Lead {
  id: string;
  phone_number: string;
  source: string;
  stage: string;
  message_count: number;
  first_seen_at: string | null;
  last_seen_at: string | null;
}

export interface LeadsResponse {
  items: Lead[];
}

export type ReservationStatus =
  | "PENDING"
  | "CONFIRMED"
  | "CHECKED_IN"
  | "CHECKED_OUT"
  | "CANCELLED"
  | "NO_SHOW";

export interface Reservation {
  id: string;
  guest_name: string;
  guest_phone: string;
  status: ReservationStatus;
  check_in_date: string | null;
  check_out_date: string | null;
  room_number: string | null;
  total_amount: number;
  created_at: string | null;
  checked_in_at: string | null;
  checked_out_at: string | null;
}

export interface ReservationsResponse {
  items: Reservation[];
}

export interface ReservationsFilters {
  from?: string;
  to?: string;
  status?: ReservationStatus | "";
  room_number?: string;
}

export type PaymentStatusType = "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED" | "REFUNDED";

export interface Payment {
  id: string;
  reservation_id: string;
  amount: number;
  status: PaymentStatusType;
  payment_method: string | null;
  transaction_id: string | null;
  created_at: string | null;
  approved_at: string | null;
  expires_at: string | null;
}

export interface PaymentsResponse {
  items: Payment[];
}

export interface PaymentsFilters {
  reservation_id?: string;
  status?: PaymentStatusType | "";
}

export interface HotelConfig {
  id: string;
  name: string;
  address: string;
  contact_phone: string;
  checkin_time: string;
  checkout_time: string;
  cancellation_policy: string;
  pet_policy: string;
  child_policy: string;
  amenities: string;
  requires_payment_for_confirmation: boolean;
  allows_reservation_without_payment: boolean;
}

export interface Room {
  id: string;
  number: string;
  room_type: string;
  daily_rate: number;
  max_guests: number;
  status: string;
}

export interface AuditEvent {
  id: number;
  event_type: string;
  client_ip: string;
  outcome: string;
  deleted_keys: number | null;
  retry_after: number | null;
  reason: string | null;
  created_at: string | null;
}

export interface AuditEventsResponse {
  items: AuditEvent[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
  };
  filters: {
    from: string | null;
    to: string | null;
    outcome: string | null;
  };
}

export interface FunnelStage {
  stage: string;
  count: number;
}

export interface FunnelResponse {
  stages: FunnelStage[];
  total: number;
}

export interface JourneyFunnelStage {
  stage: string;
  count: number;
  label?: string;
}

export interface JourneyFunnelResponse {
  stages: JourneyFunnelStage[];
  total: number;
}

export interface TimeseriesResponse {
  granularity: string;
  period: {
    from: string;
    to: string;
    source?: string;
    status?: string;
  };
  points: SeriesPoint[];
}

export type SourceFilter = "meta" | "twilio" | "";
export type StatusFilter =
  | "NEW"
  | "ENGAGED"
  | "RESERVATION_PENDING"
  | "RESERVATION_CONFIRMED"
  | "CHECKED_IN"
  | "";

export interface DashboardFilters {
  from?: string;
  to?: string;
  source?: SourceFilter;
  status?: StatusFilter;
  granularity?: "day" | "week" | "month";
}

/** Delta de comparação entre período atual e anterior */
export interface KpiDelta {
  absolute: number;
  percent: number | null;
}

/** Resposta de GET /saas/kpis/compare */
export interface KpisCompareResponse {
  granularity: string;
  current_period: { from: string; to: string; source?: string; status?: string };
  previous_period: { from: string; to: string };
  current: {
    leads_captured: number;
    ai_response_rate: number;
    reservation_confirmation_rate: number;
    checkins_completed: number;
    avg_response_time_seconds: number;
    conversion_by_source: Record<string, number>;
  };
  previous: {
    leads_captured: number;
    ai_response_rate: number;
    reservation_confirmation_rate: number;
    checkins_completed: number;
    avg_response_time_seconds: number;
    conversion_by_source: Record<string, number>;
  };
  delta: {
    leads_captured: KpiDelta;
    ai_response_rate: KpiDelta;
    reservation_confirmation_rate: KpiDelta;
    checkins_completed: KpiDelta;
    avg_response_time_seconds: KpiDelta;
  };
  series_current?: SeriesPoint[];
  series_previous?: SeriesPoint[];
}
