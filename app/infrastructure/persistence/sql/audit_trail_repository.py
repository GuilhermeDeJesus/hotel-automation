"""Serviço de Audit Trail com isolamento por hotel."""
import json
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from app.infrastructure.persistence.sql.audit_models import (
    AuditLogModel, AuditLogRetentionModel, AuditLogSummaryModel
)
from app.infrastructure.persistence.sql.models import UserModel


class AuditTrailService:
    """Serviço para gerenciamento de audit trail com isolamento por hotel."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def log_action(
        self,
        hotel_id: str,
        user_id: str,
        user_email: str,
        user_role: str,
        action: str,
        resource_type: str,
        description: str,
        resource_id: str = None,
        details: Dict = None,
        ip_address: str = None,
        user_agent: str = None,
        endpoint: str = None,
        method: str = None,
        session_id: str = None,
        request_id: str = None,
        status: str = "SUCCESS",
        error_message: str = None,
        execution_time_ms: int = None
    ) -> AuditLogModel:
        """
        Registra uma ação no audit trail.
        
        Args:
            hotel_id: ID do hotel (obrigatório para isolamento)
            user_id: ID do usuário que executou a ação
            user_email: Email do usuário
            user_role: Role do usuário
            action: Tipo de ação (CREATE, UPDATE, DELETE, LOGIN, etc.)
            resource_type: Tipo de recurso (reservation, room, user, etc.)
            description: Descrição da ação
            resource_id: ID do recurso afetado
            details: Detalhes adicionais em JSON
            ip_address: IP do cliente
            user_agent: User agent do cliente
            endpoint: Endpoint da API
            method: Método HTTP
            session_id: ID da sessão
            request_id: ID único da request
            status: Status da ação (SUCCESS, FAILED, ERROR)
            error_message: Mensagem de erro (se aplicável)
            execution_time_ms: Tempo de execução em milissegundos
        
        Returns:
            AuditLogModel criado
        """
        # Obter configuração de retenção para o hotel
        retention_config = self._get_retention_config(hotel_id)
        
        # Mascarear dados sensíveis se necessário
        masked_details = self._mask_sensitive_data(details, retention_config)
        
        # Calcular data de expiração baseado na configuração
        expires_at = self._calculate_expiry_date(action, status, retention_config)
        
        audit_log = AuditLogModel(
            id=str(uuid.uuid4()),
            hotel_id=hotel_id,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            details=masked_details,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            request_id=request_id,
            status=status,
            error_message=error_message,
            execution_time_ms=execution_time_ms,
            expires_at=expires_at
        )
        
        self.session.add(audit_log)
        self.session.flush()  # Para obter o ID sem commit ainda
        
        # Atualizar estatísticas do hotel (async)
        self._update_hotel_stats(hotel_id, action, status, execution_time_ms)
        
        return audit_log
    
    def get_hotel_logs(
        self,
        hotel_id: str,
        user: UserModel,
        limit: int = 100,
        offset: int = 0,
        start_date: datetime = None,
        end_date: datetime = None,
        action: str = None,
        resource_type: str = None,
        user_email: str = None,
        status: str = None
    ) -> List[AuditLogModel]:
        """
        Busca logs de auditoria de um hotel específico.
        
        Args:
            hotel_id: ID do hotel
            user: Usuário solicitando (para validação de permissão)
            limit: Limite de resultados
            offset: Offset para paginação
            start_date: Data inicial (opcional)
            end_date: Data final (opcional)
            action: Filtrar por ação (opcional)
            resource_type: Filtrar por tipo de recurso (opcional)
            user_email: Filtrar por email do usuário (opcional)
            status: Filtrar por status (opcional)
        
        Returns:
            Lista de AuditLogModel
        """
        # Validar permissão
        self._validate_log_access(hotel_id, user)
        
        query = self.session.query(AuditLogModel).filter(AuditLogModel.hotel_id == hotel_id)
        
        # Aplicar filtros
        if start_date:
            query = query.filter(AuditLogModel.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLogModel.timestamp <= end_date)
        if action:
            query = query.filter(AuditLogModel.action == action)
        if resource_type:
            query = query.filter(AuditLogModel.resource_type == resource_type)
        if user_email:
            query = query.filter(AuditLogModel.user_email == user_email)
        if status:
            query = query.filter(AuditLogModel.status == status)
        
        # Ordenar e paginar
        logs = query.order_by(desc(AuditLogModel.timestamp)).offset(offset).limit(limit).all()
        
        return logs
    
    def get_user_activity(
        self,
        hotel_id: str,
        user: UserModel,
        target_user_email: str,
        days: int = 30
    ) -> List[AuditLogModel]:
        """
        Busca atividades de um usuário específico no hotel.
        
        Args:
            hotel_id: ID do hotel
            user: Usuário solicitando
            target_user_email: Email do usuário alvo
            days: Número de dias para buscar
        
        Returns:
            Lista de atividades do usuário
        """
        # Validar permissão
        self._validate_log_access(hotel_id, user)
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = self.session.query(AuditLogModel).filter(
            and_(
                AuditLogModel.hotel_id == hotel_id,
                AuditLogModel.user_email == target_user_email,
                AuditLogModel.timestamp >= start_date
            )
        ).order_by(desc(AuditLogModel.timestamp)).all()
        
        return logs
    
    def get_resource_history(
        self,
        hotel_id: str,
        user: UserModel,
        resource_type: str,
        resource_id: str
    ) -> List[AuditLogModel]:
        """
        Busca histórico de alterações de um recurso específico.
        
        Args:
            hotel_id: ID do hotel
            user: Usuário solicitando
            resource_type: Tipo do recurso
            resource_id: ID do recurso
        
        Returns:
            Lista de alterações do recurso
        """
        # Validar permissão
        self._validate_log_access(hotel_id, user)
        
        logs = self.session.query(AuditLogModel).filter(
            and_(
                AuditLogModel.hotel_id == hotel_id,
                AuditLogModel.resource_type == resource_type,
                AuditLogModel.resource_id == resource_id
            )
        ).order_by(desc(AuditLogModel.timestamp)).all()
        
        return logs
    
    def get_hotel_statistics(
        self,
        hotel_id: str,
        user: UserModel,
        days: int = 30
    ) -> Dict:
        """
        Retorna estatísticas de auditoria para um hotel.
        
        Args:
            hotel_id: ID do hotel
            user: Usuário solicitando
            days: Número de dias para estatísticas
        
        Returns:
            Dicionário com estatísticas
        """
        # Validar permissão
        self._validate_log_access(hotel_id, user)
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Contadores totais
        total_logs = self.session.query(AuditLogModel).filter(
            and_(
                AuditLogModel.hotel_id == hotel_id,
                AuditLogModel.timestamp >= start_date
            )
        ).count()
        
        successful_logs = self.session.query(AuditLogModel).filter(
            and_(
                AuditLogModel.hotel_id == hotel_id,
                AuditLogModel.timestamp >= start_date,
                AuditLogModel.status == "SUCCESS"
            )
        ).count()
        
        failed_logs = self.session.query(AuditLogModel).filter(
            and_(
                AuditLogModel.hotel_id == hotel_id,
                AuditLogModel.timestamp >= start_date,
                AuditLogModel.status.in_(["FAILED", "ERROR"])
            )
        ).count()
        
        # Contadores por ação
        action_counts = self.session.query(
            AuditLogModel.action,
            func.count(AuditLogModel.id).label("count")
        ).filter(
            and_(
                AuditLogModel.hotel_id == hotel_id,
                AuditLogModel.timestamp >= start_date
            )
        ).group_by(AuditLogModel.action).all()
        
        # Contadores por recurso
        resource_counts = self.session.query(
            AuditLogModel.resource_type,
            func.count(AuditLogModel.id).label("count")
        ).filter(
            and_(
                AuditLogModel.hotel_id == hotel_id,
                AuditLogModel.timestamp >= start_date
            )
        ).group_by(AuditLogModel.resource_type).all()
        
        # Top usuários
        top_users = self.session.query(
            AuditLogModel.user_email,
            func.count(AuditLogModel.id).label("count")
        ).filter(
            and_(
                AuditLogModel.hotel_id == hotel_id,
                AuditLogModel.timestamp >= start_date
            )
        ).group_by(AuditLogModel.user_email).order_by(desc("count")).limit(10).all()
        
        return {
            "hotel_id": hotel_id,
            "period_days": days,
            "total_actions": total_logs,
            "successful_actions": successful_logs,
            "failed_actions": failed_logs,
            "success_rate": round((successful_logs / total_logs * 100) if total_logs > 0 else 0, 2),
            "action_counts": dict(action_counts),
            "resource_counts": dict(resource_counts),
            "top_users": dict(top_users),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def cleanup_expired_logs(self, hotel_id: str = None) -> int:
        """
        Remove logs expirados baseado na configuração de retenção.
        
        Args:
            hotel_id: ID do hotel específico (opcional, se None limpa todos)
        
        Returns:
            Número de logs removidos
        """
        now = datetime.utcnow()
        
        if hotel_id:
            # Limpar logs de um hotel específico
            expired_logs = self.session.query(AuditLogModel).filter(
                and_(
                    AuditLogModel.hotel_id == hotel_id,
                    AuditLogModel.expires_at <= now
                )
            ).all()
            
            count = len(expired_logs)
            for log in expired_logs:
                self.session.delete(log)
        else:
            # Limpar logs de todos os hotéis
            expired_logs = self.session.query(AuditLogModel).filter(
                AuditLogModel.expires_at <= now
            ).all()
            
            count = len(expired_logs)
            for log in expired_logs:
                self.session.delete(log)
        
        self.session.commit()
        return count
    
    # Métodos privados
    
    def _get_retention_config(self, hotel_id: str) -> AuditLogRetentionModel:
        """Obtém configuração de retenção para um hotel."""
        config = self.session.query(AuditLogRetentionModel).filter_by(hotel_id=hotel_id).first()
        
        if not config:
            # Criar configuração default
            config = AuditLogRetentionModel(
                hotel_id=hotel_id,
                default_retention_days=90,
                failed_action_retention_days=365,
                auth_action_retention_days=30,
                log_level="INFO",
                include_sensitive_data="MASKED"
            )
            self.session.add(config)
            self.session.flush()
        
        return config
    
    def _mask_sensitive_data(self, details: Dict, config: AuditLogRetentionModel) -> Optional[Dict]:
        """Mascareia dados sensíveis baseado na configuração."""
        if not details or config.include_sensitive_data == "FULL":
            return details
        
        if config.include_sensitive_data == "NONE":
            return None
        
        # Configuração "MASKED" - mascarar campos sensíveis
        masked_details = details.copy()
        sensitive_fields = ["password", "token", "credit_card", "ssn", "cpf", "api_key"]
        
        for field in sensitive_fields:
            if field in masked_details:
                masked_details[field] = "***MASKED***"
        
        return masked_details
    
    def _calculate_expiry_date(self, action: str, status: str, config: AuditLogRetentionModel) -> datetime:
        """Calcula data de expiração baseado na ação e configuração."""
        now = datetime.utcnow()
        
        if status in ["FAILED", "ERROR"]:
            return now + timedelta(days=config.failed_action_retention_days)
        elif action in ["LOGIN", "LOGOUT", "REGISTER"]:
            return now + timedelta(days=config.auth_action_retention_days)
        else:
            return now + timedelta(days=config.default_retention_days)
    
    def _validate_log_access(self, hotel_id: str, user: UserModel):
        """Valida se usuário pode acessar logs do hotel."""
        if user.role != "admin" and user.hotel_id != hotel_id:
            raise PermissionError(f"Usuário {user.email} não tem permissão para acessar logs do hotel {hotel_id}")
    
    def _update_hotel_stats(self, hotel_id: str, action: str, status: str, execution_time_ms: int):
        """Atualiza estatísticas do hotel (implementação simplificada)."""
        # Implementar lógica para atualizar estatísticas em background
        # Por enquanto, apenas registrar que a ação foi executada
        pass
