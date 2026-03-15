"""Modelos de Audit Trail para multi-tenancy."""
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.infrastructure.persistence.sql.database import Base
import uuid
from datetime import datetime


class AuditLogModel(Base):
    """Modelo para logs de auditoria com isolamento por hotel."""
    
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, index=True)
    
    # Informações do usuário
    user_id = Column(String, nullable=False, index=True)
    user_email = Column(String, nullable=False, index=True)
    user_role = Column(String, nullable=False)
    
    # Informações da ação
    action = Column(String, nullable=False, index=True)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc.
    resource_type = Column(String, nullable=False, index=True)  # reservation, room, user, etc.
    resource_id = Column(String, nullable=True, index=True)  # ID do recurso afetado
    
    # Detalhes da ação
    description = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)  # Dados adicionais em formato JSON
    
    # Informações de request
    ip_address = Column(String, nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String, nullable=True)
    method = Column(String, nullable=True)
    
    # Metadados
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    session_id = Column(String, nullable=True, index=True)
    request_id = Column(String, nullable=True, index=True)
    
    # Resultado da ação
    status = Column(String, nullable=False, default="SUCCESS", index=True)  # SUCCESS, FAILED, ERROR
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    
    # Controle de retenção
    expires_at = Column(DateTime, nullable=True, index=True)  # Para limpeza automática


class AuditLogRetentionModel(Base):
    """Modelo para configuração de retenção de logs por hotel."""
    
    __tablename__ = "audit_log_retention"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, unique=True, index=True)
    
    # Configurações de retenção
    default_retention_days = Column(Integer, nullable=False, default=90)
    failed_action_retention_days = Column(Integer, nullable=False, default=365)
    auth_action_retention_days = Column(Integer, nullable=False, default=30)
    
    # Configurações de nível de log
    log_level = Column(String, nullable=False, default="INFO")  # DEBUG, INFO, WARNING, ERROR
    include_sensitive_data = Column(String, nullable=False, default="MASKED")  # FULL, MASKED, NONE
    
    # Configurações de archiving
    archive_after_days = Column(Integer, nullable=True)  # Se None, não arquiva
    delete_after_archive_days = Column(Integer, nullable=True)  # Se None, mantém forever
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(String, nullable=False)  # ID do usuário que atualizou


class AuditLogSummaryModel(Base):
    """Modelo para resumos diários de auditoria por hotel."""
    
    __tablename__ = "audit_log_summaries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    hotel_id = Column(String, ForeignKey("hotels.id"), nullable=False, index=True)
    
    # Período do resumo
    date = Column(DateTime, nullable=False, index=True)  # Data do resumo (sem hora)
    period_type = Column(String, nullable=False, default="daily")  # daily, weekly, monthly
    
    # Contadores
    total_actions = Column(Integer, nullable=False, default=0)
    successful_actions = Column(Integer, nullable=False, default=0)
    failed_actions = Column(Integer, nullable=False, default=0)
    
    # Contadores por tipo de ação
    action_counts = Column(JSON, nullable=True)  # {"CREATE": 10, "UPDATE": 5, "DELETE": 2}
    
    # Contadores por recurso
    resource_counts = Column(JSON, nullable=True)  # {"reservation": 8, "user": 5, "room": 4}
    
    # Contadores por usuário
    user_counts = Column(JSON, nullable=True)  # {"user1@example.com": 10, "user2@example.com": 7}
    
    # Métricas de performance
    avg_execution_time_ms = Column(Integer, nullable=True)
    max_execution_time_ms = Column(Integer, nullable=True)
    total_execution_time_ms = Column(Integer, nullable=True)
    
    # Alertas
    alerts = Column(JSON, nullable=True)  # [{"type": "high_failure_rate", "count": 15}]
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Índices compostos para consultas eficientes
    __table_args__ = (
        {"schema": None},
    )
