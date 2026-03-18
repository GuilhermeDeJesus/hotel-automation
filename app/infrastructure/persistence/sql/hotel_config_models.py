"""Modelos de configuração específicos por Hotel."""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.infrastructure.persistence.sql.database import Base
import uuid
from datetime import datetime


class HotelConfigModel(Base):
    """Modelo para configurações específicas do hotel."""
    
    __tablename__ = "hotel_configs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, unique=True, index=True)
    
    # Configurações Gerais
    hotel_name = Column(String(255), nullable=False)
    hotel_description = Column(Text, nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    
    # Configurações de Pagamento (PIX)
    # Chave usada para instruções/pagamentos via PIX (Fase 0).
    pix_key = Column(String(255), nullable=True)
    
    # Configurações de Check-in/Check-out
    default_checkin_time = Column(String(10), nullable=False, default="14:00")
    default_checkout_time = Column(String(10), nullable=False, default="12:00")
    early_checkin_fee = Column(Float, nullable=True, default=0.0)
    late_checkout_fee = Column(Float, nullable=True, default=0.0)
    
    # Configurações de Cancelamento
    cancellation_policy_hours = Column(Integer, nullable=False, default=24)
    cancellation_fee_percentage = Column(Float, nullable=False, default=0.0)
    free_cancellation_hours = Column(Integer, nullable=False, default=24)
    
    # Configurações de Pagamento
    requires_payment_for_confirmation = Column(Boolean, nullable=False, default=False)
    payment_methods = Column(JSON, nullable=True)  # ["credit_card", "pix", "cash", etc.]
    payment_deadline_hours = Column(Integer, nullable=True, default=24)
    
    # Configurações de Quartos
    max_guests_per_room = Column(Integer, nullable=False, default=4)
    allows_extra_beds = Column(Boolean, nullable=False, default=True)
    extra_bed_fee = Column(Float, nullable=True, default=50.0)
    
    # Configurações de Hóspedes
    child_policy = Column(Text, nullable=True)
    pet_policy = Column(Text, nullable=True)
    smoking_policy = Column(String(20), nullable=False, default="NON_SMOKING")  # SMOKING, NON_SMOKING, MIXED
    
    # Configurações de Serviços
    breakfast_included = Column(Boolean, nullable=False, default=True)
    breakfast_price = Column(Float, nullable=True, default=0.0)
    room_service_available = Column(Boolean, nullable=False, default=True)
    room_service_hours = Column(JSON, nullable=True)  # {"start": "06:00", "end": "23:00"}
    
    # Configurações de Comunicação
    auto_send_confirmation = Column(Boolean, nullable=False, default=True)
    auto_send_reminder = Column(Boolean, nullable=False, default=True)
    reminder_hours_before = Column(Integer, nullable=True, default=24)
    
    # Configurações de WhatsApp
    whatsapp_enabled = Column(Boolean, nullable=False, default=True)
    whatsapp_number = Column(String(50), nullable=True)
    whatsapp_business_hours = Column(JSON, nullable=True)
    
    # Configurações de Rate Limiting
    rate_limit_config = Column(JSON, nullable=True)  # Configurações personalizadas de rate limit
    
    # Configurações de Audit Trail
    audit_retention_days = Column(Integer, nullable=False, default=90)
    audit_log_level = Column(String(20), nullable=False, default="INFO")  # DEBUG, INFO, WARNING, ERROR
    
    # Configurações de Moeda e Idioma
    currency = Column(String(10), nullable=False, default="BRL")
    language = Column(String(10), nullable=False, default="pt-BR")
    timezone = Column(String(50), nullable=False, default="America/Sao_Paulo")
    
    # Configurações de UI
    theme = Column(String(20), nullable=False, default="default")  # default, dark, light
    primary_color = Column(String(10), nullable=False, default="#007bff")
    logo_url = Column(String(500), nullable=True)
    
    # Configurações de Integrações
    active_integrations = Column(JSON, nullable=True)  # {"whatsapp": true, "email": true, etc.}
    webhook_urls = Column(JSON, nullable=True)  # URLs para webhooks
    
    # Configurações de Backup
    auto_backup_enabled = Column(Boolean, nullable=False, default=True)
    backup_frequency_hours = Column(Integer, nullable=False, default=24)
    backup_retention_days = Column(Integer, nullable=False, default=30)
    
    # Metadados
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(String, nullable=False)  # ID do usuário que atualizou
    
    def __repr__(self):
        return f"<HotelConfig(hotel_id={self.hotel_id}, name={self.hotel_name})>"


class HotelThemeModel(Base):
    """Modelo para temas personalizados do hotel."""
    
    __tablename__ = "hotel_themes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, unique=True, index=True)
    
    # Cores do Tema
    primary_color = Column(String(10), nullable=False, default="#007bff")
    secondary_color = Column(String(10), nullable=False, default="#6c757d")
    success_color = Column(String(10), nullable=False, default="#28a745")
    warning_color = Column(String(10), nullable=False, default="#ffc107")
    danger_color = Column(String(10), nullable=False, default="#dc3545")
    info_color = Column(String(10), nullable=False, default="#17a2b8")
    
    # Cores de Background
    body_bg_color = Column(String(10), nullable=False, default="#ffffff")
    header_bg_color = Column(String(10), nullable=False, default="#f8f9fa")
    sidebar_bg_color = Column(String(10), nullable=False, default="#343a40")
    
    # Cores de Texto
    primary_text_color = Column(String(10), nullable=False, default="#212529")
    secondary_text_color = Column(String(10), nullable=False, default="#6c757d")
    muted_text_color = Column(String(10), nullable=False, default="#adb5bd")
    
    # Configurações de Fonte
    font_family = Column(String(50), nullable=False, default="Inter, sans-serif")
    font_size_base = Column(String(10), nullable=False, default="14px")
    font_weight_normal = Column(String(10), nullable=False, default="400")
    font_weight_bold = Column(String(10), nullable=False, default="600")
    
    # Configurações de Bordas
    border_radius = Column(String(10), nullable=False, default="4px")
    border_width = Column(String(10), nullable=False, default="1px")
    border_color = Column(String(10), nullable=False, default="#dee2e6")
    
    # Configurações de Sombra
    shadow_sm = Column(String(50), nullable=False, default="0 1px 2px 0 rgba(0, 0, 0, 0.05)")
    shadow_md = Column(String(50), nullable=False, default="0 4px 6px -1px rgba(0, 0, 0, 0.1)")
    shadow_lg = Column(String(50), nullable=False, default="0 10px 15px -3px rgba(0, 0, 0, 0.1)")
    
    # Configurações de Layout
    container_max_width = Column(String(10), nullable=False, default="1200px")
    sidebar_width = Column(String(10), nullable=False, default="250px")
    header_height = Column(String(10), nullable=False, default="60px")
    
    # Configurações de Animação
    enable_animations = Column(Boolean, nullable=False, default=True)
    animation_duration = Column(String(10), nullable=False, default="0.3s")
    animation_easing = Column(String(20), nullable=False, default="ease-in-out")
    
    # Metadados
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(String, nullable=False)
    
    def __repr__(self):
        return f"<HotelTheme(hotel_id={self.hotel_id}, primary_color={self.primary_color})>"


class HotelNotificationModel(Base):
    """Modelo para configurações de notificação do hotel."""
    
    __tablename__ = "hotel_notifications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, unique=True, index=True)
    
    # Configurações de Email
    email_notifications_enabled = Column(Boolean, nullable=False, default=True)
    email_smtp_host = Column(String(255), nullable=True)
    email_smtp_port = Column(Integer, nullable=True, default=587)
    email_smtp_username = Column(String(255), nullable=True)
    email_smtp_password = Column(String(255), nullable=True)
    email_from_address = Column(String(255), nullable=True)
    email_from_name = Column(String(255), nullable=True)
    
    # Tipos de Notificação por Email
    email_on_new_reservation = Column(Boolean, nullable=False, default=True)
    email_on_payment_received = Column(Boolean, nullable=False, default=True)
    email_on_cancellation = Column(Boolean, nullable=False, default=True)
    email_on_checkin = Column(Boolean, nullable=False, default=False)
    email_on_checkout = Column(Boolean, nullable=False, default=False)
    
    # Configurações de SMS
    sms_notifications_enabled = Column(Boolean, nullable=False, default=False)
    sms_provider = Column(String(50), nullable=True)  # twilio, etc.
    sms_api_key = Column(String(255), nullable=True)
    sms_api_secret = Column(String(255), nullable=True)
    sms_from_number = Column(String(50), nullable=True)
    
    # Tipos de Notificação por SMS
    sms_on_new_reservation = Column(Boolean, nullable=False, default=False)
    sms_on_payment_received = Column(Boolean, nullable=False, default=False)
    sms_on_cancellation = Column(Boolean, nullable=False, default=False)
    sms_on_checkin_reminder = Column(Boolean, nullable=False, default=True)
    
    # Configurações de Push (Browser)
    push_notifications_enabled = Column(Boolean, nullable=False, default=True)
    push_vapid_public_key = Column(Text, nullable=True)
    push_vapid_private_key = Column(Text, nullable=True)
    push_vapid_email = Column(String(255), nullable=True)
    
    # Tipos de Notificação Push
    push_on_new_message = Column(Boolean, nullable=False, default=True)
    push_on_reservation_update = Column(Boolean, nullable=False, default=True)
    push_on_payment_status = Column(Boolean, nullable=False, default=True)
    
    # Configurações de WhatsApp
    whatsapp_notifications_enabled = Column(Boolean, nullable=False, default=True)
    whatsapp_business_api_token = Column(String(255), nullable=True)
    whatsapp_phone_number_id = Column(String(100), nullable=True)
    
    # Tipos de Notificação WhatsApp
    whatsapp_on_new_reservation = Column(Boolean, nullable=False, default=True)
    whatsapp_on_payment_received = Column(Boolean, nullable=False, default=False)
    whatsapp_on_checkin_reminder = Column(Boolean, nullable=False, default=True)
    whatsapp_on_checkout_reminder = Column(Boolean, nullable=False, default=True)
    
    # Configurações Gerais
    notification_timezone = Column(String(50), nullable=False, default="America/Sao_Paulo")
    quiet_hours_enabled = Column(Boolean, nullable=False, default=False)
    quiet_hours_start = Column(String(10), nullable=False, default="22:00")
    quiet_hours_end = Column(String(10), nullable=False, default="08:00")
    
    # Rate Limiting de Notificações
    max_notifications_per_hour = Column(Integer, nullable=False, default=10)
    max_notifications_per_day = Column(Integer, nullable=False, default=100)
    
    # Metadados
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(String, nullable=False)
    
    def __repr__(self):
        return f"<HotelNotification(hotel_id={self.hotel_id}, email_enabled={self.email_notifications_enabled})>"


class HotelIntegrationModel(Base):
    """Modelo para integrações de terceiros do hotel."""
    
    __tablename__ = "hotel_integrations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, index=True)
    
    # Informações da Integração
    integration_type = Column(String(50), nullable=False)  # pms, channel_manager, payment_gateway, etc.
    integration_name = Column(String(100), nullable=False)  # booking.com, stripe, etc.
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Configurações da Integração
    config = Column(JSON, nullable=True)  # Configurações específicas da integração
    api_credentials = Column(JSON, nullable=True)  # Credenciais da API (criptografadas)
    
    # Configurações de Sincronização
    sync_enabled = Column(Boolean, nullable=False, default=True)
    sync_frequency_minutes = Column(Integer, nullable=True, default=60)
    last_sync_at = Column(DateTime, nullable=True)
    sync_status = Column(String(20), nullable=False, default="pending")  # pending, success, error
    
    # Webhooks
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(255), nullable=True)
    webhook_events = Column(JSON, nullable=True)  # Eventos que disparam webhooks
    
    # Mapeamento de Campos
    field_mapping = Column(JSON, nullable=True)  # Mapeamento de campos entre sistemas
    
    # Configurações de Transformação de Dados
    data_transformation_rules = Column(JSON, nullable=True)
    
    # Métricas da Integração
    total_syncs = Column(Integer, nullable=False, default=0)
    successful_syncs = Column(Integer, nullable=False, default=0)
    failed_syncs = Column(Integer, nullable=False, default=0)
    last_error_message = Column(Text, nullable=True)
    
    # Metadados
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(String, nullable=False)
    
    def __repr__(self):
        return f"<HotelIntegration(hotel_id={self.hotel_id}, type={self.integration_type}, name={self.integration_name})>"
