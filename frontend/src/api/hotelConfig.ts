import { useState, useEffect } from "react";
import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
});

// Add auth token to requests
api.interceptors.request.use((config: any) => {
  const token = localStorage.getItem("auth_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Types for hotel configuration
interface HotelConfig {
  hotel_id: string;
  hotel_name: string;
  hotel_description?: string;
  contact_email?: string;
  contact_phone?: string;
  default_checkin_time: string;
  default_checkout_time: string;
  early_checkin_fee?: number;
  late_checkout_fee?: number;
  cancellation_policy_hours: number;
  cancellation_fee_percentage: number;
  free_cancellation_hours: number;
  requires_payment_for_confirmation: boolean;
  payment_methods?: string[];
  payment_deadline_hours?: number;
  max_guests_per_room: number;
  allows_extra_beds: boolean;
  extra_bed_fee?: number;
  child_policy?: string;
  pet_policy?: string;
  smoking_policy: string;
  breakfast_included: boolean;
  breakfast_price?: number;
  room_service_available: boolean;
  room_service_hours?: Record<string, string>;
  auto_send_confirmation: boolean;
  auto_send_reminder: boolean;
  reminder_hours_before?: number;
  whatsapp_enabled: boolean;
  whatsapp_number?: string;
  whatsapp_business_hours?: Record<string, string>;
  rate_limit_config?: Record<string, any>;
  audit_retention_days: number;
  audit_log_level: string;
  currency: string;
  language: string;
  timezone: string;
  theme: string;
  primary_color: string;
  logo_url?: string;
  active_integrations?: Record<string, boolean>;
  webhook_urls?: Record<string, string>;
  auto_backup_enabled: boolean;
  backup_frequency_hours: number;
  backup_retention_days: number;
  created_at: string;
  updated_at: string;
}

interface HotelTheme {
  hotel_id: string;
  primary_color: string;
  secondary_color: string;
  success_color: string;
  warning_color: string;
  danger_color: string;
  info_color: string;
  body_bg_color: string;
  header_bg_color: string;
  sidebar_bg_color: string;
  primary_text_color: string;
  secondary_text_color: string;
  muted_text_color: string;
  font_family: string;
  font_size_base: string;
  font_weight_normal: string;
  font_weight_bold: string;
  border_radius: string;
  border_width: string;
  border_color: string;
  shadow_sm: string;
  shadow_md: string;
  shadow_lg: string;
  container_max_width: string;
  sidebar_width: string;
  header_height: string;
  enable_animations: boolean;
  animation_duration: string;
  animation_easing: string;
}

interface HotelNotifications {
  hotel_id: string;
  email_notifications_enabled: boolean;
  email_smtp_host?: string;
  email_smtp_port?: number;
  email_smtp_username?: string;
  email_from_address?: string;
  email_from_name?: string;
  email_on_new_reservation: boolean;
  email_on_payment_received: boolean;
  email_on_cancellation: boolean;
  email_on_checkin: boolean;
  email_on_checkout: boolean;
  sms_notifications_enabled: boolean;
  sms_provider?: string;
  sms_from_number?: string;
  sms_on_new_reservation: boolean;
  sms_on_payment_received: boolean;
  sms_on_cancellation: boolean;
  sms_on_checkin_reminder: boolean;
  push_notifications_enabled: boolean;
  push_on_new_message: boolean;
  push_on_reservation_update: boolean;
  push_on_payment_status: boolean;
  whatsapp_notifications_enabled: boolean;
  whatsapp_on_new_reservation: boolean;
  whatsapp_on_payment_received: boolean;
  whatsapp_on_checkin_reminder: boolean;
  whatsapp_on_checkout_reminder: boolean;
  notification_timezone: string;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  max_notifications_per_hour: number;
  max_notifications_per_day: number;
}

interface HotelIntegration {
  id: string;
  integration_type: string;
  integration_name: string;
  is_active: boolean;
  sync_enabled: boolean;
  sync_frequency_minutes: number;
  last_sync_at?: string;
  sync_status: string;
  total_syncs: number;
  successful_syncs: number;
  failed_syncs: number;
  last_error_message?: string;
  created_at: string;
  updated_at: string;
}

interface HotelSettingsSummary {
  hotel_id: string;
  hotel_name: string;
  basic_config: {
    contact_email?: string;
    contact_phone?: string;
    currency: string;
    language: string;
    timezone: string;
  };
  operational_config: {
    checkin_time: string;
    checkout_time: string;
    requires_payment: boolean;
    whatsapp_enabled: boolean;
  };
  theme: {
    primary_color: string;
    theme: string;
    logo_url?: string;
  };
  notifications: {
    email_enabled: boolean;
    sms_enabled: boolean;
    whatsapp_enabled: boolean;
    push_enabled: boolean;
  };
  integrations: {
    total_count: number;
    active_count: number;
    types: string[];
  };
}

// API functions for hotel configuration
export const hotelConfigApi = {
  // Get hotel configuration
  getHotelConfig: async (hotelId: string): Promise<HotelConfig> => {
    const response = await api.get(`/config/hotel/${hotelId}/config`);
    return response.data;
  },

  // Update hotel configuration
  updateHotelConfig: async (hotelId: string, config: Partial<HotelConfig>): Promise<{ message: string; hotel_id: string; updated_at: string }> => {
    const response = await api.put(`/config/hotel/${hotelId}/config`, config);
    return response.data;
  },

  // Get hotel theme
  getHotelTheme: async (hotelId: string): Promise<HotelTheme> => {
    const response = await api.get(`/config/hotel/${hotelId}/theme`);
    return response.data;
  },

  // Update hotel theme
  updateHotelTheme: async (hotelId: string, theme: Partial<HotelTheme>): Promise<{ message: string; hotel_id: string; updated_at: string }> => {
    const response = await api.put(`/config/hotel/${hotelId}/theme`, theme);
    return response.data;
  },

  // Get hotel notifications
  getHotelNotifications: async (hotelId: string): Promise<HotelNotifications> => {
    const response = await api.get(`/config/hotel/${hotelId}/notifications`);
    return response.data;
  },

  // Update hotel notifications
  updateHotelNotifications: async (hotelId: string, notifications: Partial<HotelNotifications>): Promise<{ message: string; hotel_id: string; updated_at: string }> => {
    const response = await api.put(`/config/hotel/${hotelId}/notifications`, notifications);
    return response.data;
  },

  // Get hotel integrations
  getHotelIntegrations: async (hotelId: string): Promise<{ hotel_id: string; integrations: HotelIntegration[] }> => {
    const response = await api.get(`/config/hotel/${hotelId}/integrations`);
    return response.data;
  },

  // Create hotel integration
  createHotelIntegration: async (hotelId: string, integration: {
    integration_type: string;
    integration_name: string;
    config?: Record<string, any>;
    api_credentials?: Record<string, string>;
    sync_enabled?: boolean;
    sync_frequency_minutes?: number;
    webhook_url?: string;
    webhook_secret?: string;
    webhook_events?: string[];
    field_mapping?: Record<string, string>;
    data_transformation_rules?: Record<string, any>;
  }): Promise<{ message: string; integration_id: string; integration_type: string; integration_name: string; created_at: string }> => {
    const response = await api.post(`/config/hotel/${hotelId}/integrations`, integration);
    return response.data;
  },

  // Update hotel integration
  updateHotelIntegration: async (hotelId: string, integrationId: string, integration: Partial<HotelIntegration>): Promise<{ message: string; integration_id: string; updated_at: string }> => {
    const response = await api.put(`/config/hotel/${hotelId}/integrations/${integrationId}`, integration);
    return response.data;
  },

  // Delete hotel integration
  deleteHotelIntegration: async (hotelId: string, integrationId: string): Promise<{ message: string; integration_id: string }> => {
    const response = await api.delete(`/config/hotel/${hotelId}/integrations/${integrationId}`);
    return response.data;
  },

  // Get hotel settings summary
  getHotelSettingsSummary: async (hotelId: string): Promise<HotelSettingsSummary> => {
    const response = await api.get(`/config/hotel/${hotelId}/summary`);
    return response.data;
  },

  // Reset hotel to defaults
  resetHotelToDefaults: async (hotelId: string): Promise<{ message: string; hotel_id: string; reset_by: string }> => {
    const response = await api.post(`/config/hotel/${hotelId}/reset`);
    return response.data;
  },
};

// Custom hooks for hotel configuration
export const useHotelConfig = (hotelId: string | null) => {
  const [config, setConfig] = useState<HotelConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setLoading(true);
        setError(null);
        if (!hotelId) {
          setConfig(null);
          setLoading(false);
          return;
        }
        const data = await hotelConfigApi.getHotelConfig(hotelId);
        setConfig(data);
      } catch (err: any) {
        setError(err.message || "Failed to fetch hotel configuration");
      } finally {
        setLoading(false);
      }
    };

    if (hotelId) {
      fetchConfig();
    }
  }, [hotelId]);

  const updateConfig = async (newConfig: Partial<HotelConfig>) => {
    try {
      setError(null);
      if (!hotelId) {
        throw new Error("Hotel não definido.");
      }
      const result = await hotelConfigApi.updateHotelConfig(hotelId, newConfig);
      if (config) {
        setConfig({ ...config, ...newConfig });
      }
      return result;
    } catch (err: any) {
      setError(err.message || "Failed to update hotel configuration");
      throw err;
    }
  };

  return { config, loading, error, updateConfig };
};

export const useHotelTheme = (hotelId: string) => {
  const [theme, setTheme] = useState<HotelTheme | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTheme = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await hotelConfigApi.getHotelTheme(hotelId);
        setTheme(data);
      } catch (err: any) {
        setError(err.message || "Failed to fetch hotel theme");
      } finally {
        setLoading(false);
      }
    };

    if (hotelId) {
      fetchTheme();
    }
  }, [hotelId]);

  const updateTheme = async (newTheme: Partial<HotelTheme>) => {
    try {
      setError(null);
      const result = await hotelConfigApi.updateHotelTheme(hotelId, newTheme);
      if (theme) {
        setTheme({ ...theme, ...newTheme });
      }
      return result;
    } catch (err: any) {
      setError(err.message || "Failed to update hotel theme");
      throw err;
    }
  };

  return { theme, loading, error, updateTheme };
};

export const useHotelNotifications = (hotelId: string) => {
  const [notifications, setNotifications] = useState<HotelNotifications | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await hotelConfigApi.getHotelNotifications(hotelId);
        setNotifications(data);
      } catch (err: any) {
        setError(err.message || "Failed to fetch hotel notifications");
      } finally {
        setLoading(false);
      }
    };

    if (hotelId) {
      fetchNotifications();
    }
  }, [hotelId]);

  const updateNotifications = async (newNotifications: Partial<HotelNotifications>) => {
    try {
      setError(null);
      const result = await hotelConfigApi.updateHotelNotifications(hotelId, newNotifications);
      if (notifications) {
        setNotifications({ ...notifications, ...newNotifications });
      }
      return result;
    } catch (err: any) {
      setError(err.message || "Failed to update hotel notifications");
      throw err;
    }
  };

  return { notifications, loading, error, updateNotifications };
};

export const useHotelIntegrations = (hotelId: string) => {
  const [integrations, setIntegrations] = useState<HotelIntegration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchIntegrations = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await hotelConfigApi.getHotelIntegrations(hotelId);
      setIntegrations(data.integrations);
    } catch (err: any) {
      setError(err.message || "Failed to fetch hotel integrations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (hotelId) {
      fetchIntegrations();
    }
  }, [hotelId]);

  const createIntegration = async (integration: {
    integration_type: string;
    integration_name: string;
    config?: Record<string, any>;
    api_credentials?: Record<string, string>;
    sync_enabled?: boolean;
    sync_frequency_minutes?: number;
    webhook_url?: string;
    webhook_secret?: string;
    webhook_events?: string[];
    field_mapping?: Record<string, string>;
    data_transformation_rules?: Record<string, any>;
  }) => {
    try {
      setError(null);
      const result = await hotelConfigApi.createHotelIntegration(hotelId, integration);
      await fetchIntegrations(); // Refresh list
      return result;
    } catch (err: any) {
      setError(err.message || "Failed to create hotel integration");
      throw err;
    }
  };

  const updateIntegration = async (integrationId: string, integration: Partial<HotelIntegration>) => {
    try {
      setError(null);
      const result = await hotelConfigApi.updateHotelIntegration(hotelId, integrationId, integration);
      await fetchIntegrations(); // Refresh list
      return result;
    } catch (err: any) {
      setError(err.message || "Failed to update hotel integration");
      throw err;
    }
  };

  const deleteIntegration = async (integrationId: string) => {
    try {
      setError(null);
      const result = await hotelConfigApi.deleteHotelIntegration(hotelId, integrationId);
      await fetchIntegrations(); // Refresh list
      return result;
    } catch (err: any) {
      setError(err.message || "Failed to delete hotel integration");
      throw err;
    }
  };

  return { integrations, loading, error, createIntegration, updateIntegration, deleteIntegration, refreshIntegrations: fetchIntegrations };
};

export const useHotelSettingsSummary = (hotelId: string) => {
  const [summary, setSummary] = useState<HotelSettingsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await hotelConfigApi.getHotelSettingsSummary(hotelId);
        setSummary(data);
      } catch (err: any) {
        setError(err.message || "Failed to fetch hotel settings summary");
      } finally {
        setLoading(false);
      }
    };

    if (hotelId) {
      fetchSummary();
    }
  }, [hotelId]);

  return { summary, loading, error };
};

// Utility functions for configuration
export const validateConfig = (config: Partial<HotelConfig>): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];

  if (config.default_checkin_time && !/^([01]?[0-9]|2[0-3]):[0-5][0-9]$/.test(config.default_checkin_time)) {
    errors.push("Horário de check-in inválido. Use formato HH:MM");
  }

  if (config.default_checkout_time && !/^([01]?[0-9]|2[0-3]):[0-5][0-9]$/.test(config.default_checkout_time)) {
    errors.push("Horário de check-out inválido. Use formato HH:MM");
  }

  if (config.cancellation_policy_hours && config.cancellation_policy_hours < 0) {
    errors.push("Política de cancelamento deve ser um número positivo");
  }

  if (config.cancellation_fee_percentage && (config.cancellation_fee_percentage < 0 || config.cancellation_fee_percentage > 100)) {
    errors.push("Percentual de taxa de cancelamento deve estar entre 0 e 100");
  }

  if (config.max_guests_per_room && config.max_guests_per_room < 1) {
    errors.push("Máximo de hóspedes por quarto deve ser pelo menos 1");
  }

  if (config.backup_frequency_hours && config.backup_frequency_hours < 1) {
    errors.push("Frequência de backup deve ser pelo menos 1 hora");
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
};

export const validateTheme = (theme: Partial<HotelTheme>): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];

  const colorRegex = /^#[0-9A-Fa-f]{6}$/;

  if (theme.primary_color && !colorRegex.test(theme.primary_color)) {
    errors.push("Cor primária inválida. Use formato #RRGGBB");
  }

  if (theme.secondary_color && !colorRegex.test(theme.secondary_color)) {
    errors.push("Cor secundária inválida. Use formato #RRGGBB");
  }

  if (theme.success_color && !colorRegex.test(theme.success_color)) {
    errors.push("Cor de sucesso inválida. Use formato #RRGGBB");
  }

  if (theme.warning_color && !colorRegex.test(theme.warning_color)) {
    errors.push("Cor de aviso inválida. Use formato #RRGGBB");
  }

  if (theme.danger_color && !colorRegex.test(theme.danger_color)) {
    errors.push("Cor de perigo inválida. Use formato #RRGGBB");
  }

  if (theme.info_color && !colorRegex.test(theme.info_color)) {
    errors.push("Cor de informação inválida. Use formato #RRGGBB");
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
};
