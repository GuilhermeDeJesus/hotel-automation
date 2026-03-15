import { useState, useEffect } from "react";
import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Types for dashboard data
interface DashboardStats {
  hotel_id: string;
  hotel_name: string;
  period_days: number;
  total_reservations: number;
  confirmed_reservations: number;
  pending_reservations: number;
  cancelled_reservations: number;
  total_revenue: number;
  occupancy_rate: number;
  total_rooms: number;
  occupied_rooms: number;
  available_rooms: number;
  maintenance_rooms: number;
  total_customers: number;
  new_customers_this_period: number;
  total_payments: number;
  successful_payments: number;
  failed_payments: number;
  total_support_tickets: number;
  open_tickets: number;
  resolved_tickets: number;
  average_resolution_time_hours: number;
  room_orders_count: number;
  pending_orders: number;
  completed_orders: number;
}

interface RevenueAnalytics {
  daily_revenue: Array<{ date: string; revenue: number }>;
  monthly_revenue: Array<{ month: string; revenue: number }>;
  revenue_by_room_type: Record<string, number>;
  top_selling_rooms: Array<{ room_number: string; revenue: number; occupancy: number }>;
  payment_methods_breakdown: Record<string, number>;
}

interface OccupancyAnalytics {
  daily_occupancy: Array<{ date: string; occupancy_rate: number }>;
  occupancy_by_room_type: Record<string, number>;
  peak_occupancy_days: Array<{ date: string; occupancy_rate: number }>;
  low_occupancy_days: Array<{ date: string; occupancy_rate: number }>;
  average_stay_duration: number;
}

interface CustomerAnalytics {
  new_customers_trend: Array<{ date: string; count: number }>;
  customer_distribution_by_source: Record<string, number>;
  repeat_customers: number;
  customer_satisfaction_score: number;
  top_customers_by_revenue: Array<{ email: string; name: string; revenue: number }>;
}

interface RecentActivity {
  type: string;
  id: string;
  description: string;
  timestamp: string;
  status: string;
}

interface PerformanceMetrics {
  hotel_id: string;
  period_days: number;
  metrics: {
    average_response_time_minutes: number;
    customer_satisfaction_score: number;
    staff_performance_score: number;
    revenue_per_available_room: number;
    cost_per_occupied_room: number;
    gross_operating_profit_margin: number;
  };
}

// API functions for dashboard
export const dashboardApi = {
  // Get dashboard stats for a specific hotel
  getDashboardStats: async (hotelId: string, days: number = 30): Promise<DashboardStats> => {
    const response = await api.get(`/dashboard/hotel/${hotelId}/stats?days=${days}`);
    return response.data;
  },

  // Get revenue analytics
  getRevenueAnalytics: async (hotelId: string, days: number = 30): Promise<RevenueAnalytics> => {
    const response = await api.get(`/dashboard/hotel/${hotelId}/revenue-analytics?days=${days}`);
    return response.data;
  },

  // Get occupancy analytics
  getOccupancyAnalytics: async (hotelId: string, days: number = 30): Promise<OccupancyAnalytics> => {
    const response = await api.get(`/dashboard/hotel/${hotelId}/occupancy-analytics?days=${days}`);
    return response.data;
  },

  // Get customer analytics
  getCustomerAnalytics: async (hotelId: string, days: number = 30): Promise<CustomerAnalytics> => {
    const response = await api.get(`/dashboard/hotel/${hotelId}/customer-analytics?days=${days}`);
    return response.data;
  },

  // Get recent activity
  getRecentActivity: async (hotelId: string, limit: number = 20): Promise<{ activities: RecentActivity[] }> => {
    const response = await api.get(`/dashboard/hotel/${hotelId}/recent-activity?limit=${limit}`);
    return response.data;
  },

  // Get performance metrics
  getPerformanceMetrics: async (hotelId: string, days: number = 30): Promise<PerformanceMetrics> => {
    const response = await api.get(`/dashboard/hotel/${hotelId}/performance-metrics?days=${days}`);
    return response.data;
  },
};

// Custom hooks for dashboard data
export const useDashboardStats = (hotelId: string, days: number = 30) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await dashboardApi.getDashboardStats(hotelId, days);
        setStats(data);
      } catch (err: any) {
        setError(err.message || "Failed to fetch dashboard stats");
      } finally {
        setLoading(false);
      }
    };

    if (hotelId) {
      fetchStats();
    }
  }, [hotelId, days]);

  return { stats, loading, error };
};

export const useRevenueAnalytics = (hotelId: string, days: number = 30) => {
  const [analytics, setAnalytics] = useState<RevenueAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await dashboardApi.getRevenueAnalytics(hotelId, days);
        setAnalytics(data);
      } catch (err: any) {
        setError(err.message || "Failed to fetch revenue analytics");
      } finally {
        setLoading(false);
      }
    };

    if (hotelId) {
      fetchAnalytics();
    }
  }, [hotelId, days]);

  return { analytics, loading, error };
};

export const useOccupancyAnalytics = (hotelId: string, days: number = 30) => {
  const [analytics, setAnalytics] = useState<OccupancyAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await dashboardApi.getOccupancyAnalytics(hotelId, days);
        setAnalytics(data);
      } catch (err: any) {
        setError(err.message || "Failed to fetch occupancy analytics");
      } finally {
        setLoading(false);
      }
    };

    if (hotelId) {
      fetchAnalytics();
    }
  }, [hotelId, days]);

  return { analytics, loading, error };
};

export const useCustomerAnalytics = (hotelId: string, days: number = 30) => {
  const [analytics, setAnalytics] = useState<CustomerAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await dashboardApi.getCustomerAnalytics(hotelId, days);
        setAnalytics(data);
      } catch (err: any) {
        setError(err.message || "Failed to fetch customer analytics");
      } finally {
        setLoading(false);
      }
    };

    if (hotelId) {
      fetchAnalytics();
    }
  }, [hotelId, days]);

  return { analytics, loading, error };
};

export const useRecentActivity = (hotelId: string, limit: number = 20) => {
  const [activities, setActivities] = useState<RecentActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchActivities = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await dashboardApi.getRecentActivity(hotelId, limit);
        setActivities(data.activities);
      } catch (err: any) {
        setError(err.message || "Failed to fetch recent activity");
      } finally {
        setLoading(false);
      }
    };

    if (hotelId) {
      fetchActivities();
    }
  }, [hotelId, limit]);

  return { activities, loading, error };
};

export const usePerformanceMetrics = (hotelId: string, days: number = 30) => {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await dashboardApi.getPerformanceMetrics(hotelId, days);
        setMetrics(data);
      } catch (err: any) {
        setError(err.message || "Failed to fetch performance metrics");
      } finally {
        setLoading(false);
      }
    };

    if (hotelId) {
      fetchMetrics();
    }
  }, [hotelId, days]);

  return { metrics, loading, error };
};

// Utility functions for formatting data
export const formatCurrency = (amount: number, currency: string = "BRL"): string => {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency,
  }).format(amount);
};

export const formatPercentage = (value: number): string => {
  return `${value.toFixed(1)}%`;
};

export const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString("pt-BR");
};

export const formatDateTime = (dateString: string): string => {
  return new Date(dateString).toLocaleString("pt-BR");
};

// Color utilities for dashboard
export const getStatusColor = (status: string): string => {
  const colors: Record<string, string> = {
    CONFIRMED: "#28a745",
    PENDING: "#ffc107",
    CANCELLED: "#dc3545",
    CHECKED_IN: "#17a2b8",
    CHECKED_OUT: "#6c757d",
    COMPLETED: "#28a745",
    FAILED: "#dc3545",
    OPEN: "#ffc107",
    CLOSED: "#28a745",
  };
  return colors[status] || "#6c757d";
};

export const getOccupancyColor = (rate: number): string => {
  if (rate >= 80) return "#28a745"; // Green - High occupancy
  if (rate >= 60) return "#ffc107"; // Yellow - Medium occupancy
  return "#dc3545"; // Red - Low occupancy
};

export const getRevenueColor = (revenue: number, target: number): string => {
  if (revenue >= target) return "#28a745"; // Green - Above target
  if (revenue >= target * 0.8) return "#ffc107"; // Yellow - Close to target
  return "#dc3545"; // Red - Below target
};
