from sqlalchemy import Column, Integer, String, DateTime, Float, Date, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class UserModel(Base):
    """Tabela de Usuários para autenticação e RBAC"""
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="user")  # admin, manager, staff, user
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class RoomModel(Base):
    """Tabela de Quartos do Hotel"""
    __tablename__ = "rooms"
    __table_args__ = (UniqueConstraint("hotel_id", "number", name="uq_rooms_hotel_number"),)

    id = Column(String, primary_key=True)
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, index=True)
    number = Column(String(10), nullable=False, index=True)
    room_type = Column(String(50), nullable=False)  # SINGLE, DOUBLE, SUITE
    daily_rate = Column(Float, nullable=False)
    max_guests = Column(Integer, default=2)
    status = Column(String(20), nullable=False, index=True, default="AVAILABLE")  # AVAILABLE, OCCUPIED, MAINTENANCE
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CustomerModel(Base):
    """Tabela de Clientes/Hóspedes"""
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("hotel_id", "document", name="uq_customers_hotel_document"),)

    id = Column(String, primary_key=True)
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), index=True)
    email = Column(String(255), index=True)
    document = Column(String(20), index=True)
    status = Column(String(20), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relacionamentos
    reservations = relationship("ReservationModel", back_populates="customer")


class ReservationModel(Base):
    """Tabela de Reservas"""
    __tablename__ = "reservations"

    id = Column(String, primary_key=True)
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, index=True)
    
    # Dados do hóspede
    guest_name = Column(String(255), nullable=False)
    guest_phone = Column(String(20), index=True, nullable=False)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=True)
    
    # Status e período
    status = Column(String(20), nullable=False, index=True)
    check_in_date = Column(Date)
    check_out_date = Column(Date)
    
    # Detalhes da estadia
    room_number = Column(String(10))
    total_amount = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    checked_in_at = Column(DateTime)
    checked_out_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Notas adicionais
    notes = Column(Text)

    # 6.1 Check-in antecipado
    guest_document = Column(String(20))
    estimated_arrival_time = Column(String(10))
    pre_checkin_completed_at = Column(DateTime)

    # 6.4 Self-check-in e chave digital
    digital_key_code = Column(String(20))

    # 6.8 Segurança e compliance (LGPD)
    consent_terms_accepted_at = Column(DateTime)
    consent_marketing = Column(Boolean, default=False)

    # Relacionamentos
    customer = relationship("CustomerModel", back_populates="reservations")
    payments = relationship("PaymentModel", back_populates="reservation")


class PaymentModel(Base):
    """Tabela de Pagamentos"""
    __tablename__ = "payments"

    id = Column(String, primary_key=True)
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, index=True)
    reservation_id = Column(String, ForeignKey("reservations.id"), nullable=False, index=True)
    
    # Dados do pagamento
    amount = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, index=True, default="PENDING")
    payment_method = Column(String(50))
    transaction_id = Column(String(255), unique=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    approved_at = Column(DateTime)
    expires_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relacionamentos
    reservation = relationship("ReservationModel", back_populates="payments")


class HotelModel(Base):
    """Tabela de Hotel (configuracoes e politicas)"""
    __tablename__ = "hotels"

    id = Column(String, primary_key=True)
    name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    contact_phone = Column(String(30), nullable=False)
    checkin_time = Column(String(10), nullable=False)
    checkout_time = Column(String(10), nullable=False)
    cancellation_policy = Column(Text, nullable=False)
    pet_policy = Column(Text, nullable=False)
    child_policy = Column(Text, nullable=False)
    amenities = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    requires_payment_for_confirmation = Column(Boolean, default=False, nullable=False)
    allows_reservation_without_payment = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ConversationCacheModel(Base):
    """Tabela de Cache de Conversas (WhatsApp)"""
    __tablename__ = "conversation_cache"
    __table_args__ = (UniqueConstraint("hotel_id", "phone_number", name="uq_conversation_cache_hotel_phone"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)
    context_data = Column(Text)  # JSON string
    last_message = Column(Text)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class LeadModel(Base):
    """Tabela de leads SaaS para acompanhamento de funil."""
    __tablename__ = "saas_leads"
    __table_args__ = (UniqueConstraint("hotel_id", "phone_number", name="uq_saas_leads_hotel_phone"),)

    id = Column(String, primary_key=True)
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)
    source = Column(String(20), nullable=False, index=True, default="unknown")
    stage = Column(String(40), nullable=False, index=True, default="NEW")
    message_count = Column(Integer, nullable=False, default=0)
    first_seen_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    last_seen_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AnalyticsEventModel(Base):
    """Tabela de eventos analíticos para KPI e funil."""
    __tablename__ = "saas_analytics_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)
    source = Column(String(20), nullable=False, index=True, default="unknown")
    event_type = Column(String(50), nullable=False, index=True)
    success = Column(Boolean, nullable=False, default=True)
    response_time_ms = Column(Integer, nullable=True)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)


class SaaSAdminAuditEventModel(Base):
    """Tabela de auditoria administrativa para operações SaaS."""
    __tablename__ = "saas_admin_audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(80), nullable=False, index=True)
    client_ip = Column(String(80), nullable=False, index=True)
    outcome = Column(String(40), nullable=False, index=True)
    deleted_keys = Column(Integer, nullable=True)
    retry_after = Column(Integer, nullable=True)
    reason = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)


class SupportTicketModel(Base):
    """6.6 Resolução de problemas - tickets de suporte."""
    __tablename__ = "support_tickets"

    id = Column(String, primary_key=True)
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, index=True)
    reservation_id = Column(String, ForeignKey("reservations.id"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, index=True, default="OPEN")
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    resolved_at = Column(DateTime)


class RoomOrderModel(Base):
    """6.5 Pedidos durante a estadia (room service)."""
    __tablename__ = "room_orders"

    id = Column(String, primary_key=True)
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, index=True)
    reservation_id = Column(String, ForeignKey("reservations.id"), nullable=False, index=True)
    items_json = Column(Text, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class ProactiveMessageLogModel(Base):
    """6.2 Comunicação proativa - log de mensagens enviadas."""
    __tablename__ = "proactive_message_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, index=True)
    reservation_id = Column(String, nullable=False, index=True)
    message_type = Column(String(50), nullable=False)
    sent_at = Column(DateTime, default=datetime.now, nullable=False)


class SaaSAuditMetricsSnapshotModel(Base):
    """Snapshot diário das métricas agregadas de auditoria SaaS."""
    __tablename__ = "saas_audit_metrics_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(Date, nullable=False, unique=True, index=True)
    total_attempts = Column(Integer, nullable=False, default=0)
    rate_limited_count = Column(Integer, nullable=False, default=0)
    rate_limited_ratio = Column(Float, nullable=False, default=0.0)
    alert_status = Column(String(20), nullable=False, default="healthy")
    warning_threshold = Column(Float, nullable=False, default=0.2)
    critical_threshold = Column(Float, nullable=False, default=0.5)
    by_outcome_json = Column(Text, nullable=False, default="{}")
    top_ips_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)