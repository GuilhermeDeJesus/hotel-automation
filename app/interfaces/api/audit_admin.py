"""Endpoints de administração de Audit Trail por Hotel."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

from app.interfaces.dependencies.auth import get_current_user
from app.infrastructure.persistence.sql.models import UserModel
from app.infrastructure.persistence.sql.audit_trail_repository import AuditTrailService
from app.infrastructure.persistence.sql.database import SessionLocal
from app.interfaces.middleware.audit_trail_middleware import log_audit_action


router = APIRouter(prefix="/admin/audit", tags=["Audit Trail Admin"])


# Pydantic models
class AuditLogResponse(BaseModel):
    id: str
    hotel_id: str
    user_id: str
    user_email: str
    user_role: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    description: str
    ip_address: Optional[str]
    endpoint: Optional[str]
    method: Optional[str]
    timestamp: datetime
    status: str
    error_message: Optional[str]
    execution_time_ms: Optional[int]
    
    class Config:
        from_attributes = True


class HotelStatisticsResponse(BaseModel):
    hotel_id: str
    period_days: int
    total_actions: int
    successful_actions: int
    failed_actions: int
    success_rate: float
    action_counts: dict
    resource_counts: dict
    top_users: dict
    generated_at: str


@router.get("/hotels/{hotel_id}/logs", response_model=List[AuditLogResponse])
def get_hotel_audit_logs(
    hotel_id: str,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    user_email: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retorna logs de auditoria de um hotel específico.
    
    - Admin: pode ver logs de qualquer hotel
    - Outros: só podem ver logs do próprio hotel
    """
    session = SessionLocal()
    try:
        audit_service = AuditTrailService(session)
        logs = audit_service.get_hotel_logs(
            hotel_id=hotel_id,
            user=current_user,
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
            action=action,
            resource_type=resource_type,
            user_email=user_email,
            status=status
        )
        
        # Logar a ação de visualização
        log_audit_action(
            hotel_id=current_user.hotel_id or hotel_id,
            user=current_user,
            action="VIEW",
            resource_type="audit_logs",
            description=f"Visualizou logs de auditoria do hotel {hotel_id}",
            resource_id=hotel_id,
            details={
                "filters": {
                    "limit": limit,
                    "offset": offset,
                    "action": action,
                    "resource_type": resource_type,
                    "user_email": user_email,
                    "status": status
                }
            }
        )
        
        return logs
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar logs: {str(e)}"
        )
    finally:
        session.close()


@router.get("/hotels/{hotel_id}/statistics", response_model=HotelStatisticsResponse)
def get_hotel_audit_statistics(
    hotel_id: str,
    days: int = Query(30, le=365, ge=1),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retorna estatísticas de auditoria para um hotel.
    
    Útil para dashboard de monitoramento.
    """
    session = SessionLocal()
    try:
        audit_service = AuditTrailService(session)
        stats = audit_service.get_hotel_statistics(hotel_id, current_user, days)
        
        return stats
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar estatísticas: {str(e)}"
        )
    finally:
        session.close()


@router.get("/hotels/{hotel_id}/users/{user_email}/activity")
def get_user_activity(
    hotel_id: str,
    user_email: str,
    days: int = Query(30, le=365, ge=1),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retorna atividades de um usuário específico no hotel.
    
    Útil para investigação de comportamento suspeito.
    """
    session = SessionLocal()
    try:
        audit_service = AuditTrailService(session)
        activities = audit_service.get_user_activity(hotel_id, current_user, user_email, days)
        
        # Logar a investigação
        log_audit_action(
            hotel_id=current_user.hotel_id or hotel_id,
            user=current_user,
            action="INVESTIGATE",
            resource_type="user_activity",
            description=f"Investigou atividades do usuário {user_email}",
            resource_id=user_email,
            details={"days": days, "activity_count": len(activities)}
        )
        
        return {
            "hotel_id": hotel_id,
            "user_email": user_email,
            "period_days": days,
            "activities": activities,
            "total_activities": len(activities)
        }
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar atividades: {str(e)}"
        )
    finally:
        session.close()


@router.get("/hotels/{hotel_id}/resources/{resource_type}/{resource_id}/history")
def get_resource_history(
    hotel_id: str,
    resource_type: str,
    resource_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retorna histórico de alterações de um recurso específico.
    
    Útil para auditoria de dados.
    """
    session = SessionLocal()
    try:
        audit_service = AuditTrailService(session)
        history = audit_service.get_resource_history(hotel_id, current_user, resource_type, resource_id)
        
        return {
            "hotel_id": hotel_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "history": history,
            "total_changes": len(history)
        }
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar histórico: {str(e)}"
        )
    finally:
        session.close()


@router.post("/cleanup")
def cleanup_expired_logs(
    hotel_id: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Limpa logs expirados baseado na configuração de retenção.
    
    Apenas administradores podem executar esta ação.
    
    - hotel_id: opcional, se não informado limpa logs de todos os hotéis
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem executar limpeza de logs"
        )
    
    session = SessionLocal()
    try:
        audit_service = AuditTrailService(session)
        deleted_count = audit_service.cleanup_expired_logs(hotel_id)
        
        # Logar a ação de limpeza
        log_audit_action(
            hotel_id=current_user.hotel_id or "system",
            user=current_user,
            action="CLEANUP",
            resource_type="audit_logs",
            description=f"Limpeza de logs expirados",
            resource_id=hotel_id or "all",
            details={"deleted_count": deleted_count, "target_hotel": hotel_id}
        )
        
        return {
            "message": "Limpeza executada com sucesso",
            "deleted_logs": deleted_count,
            "target_hotel": hotel_id or "all_hotels",
            "executed_by": current_user.email
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao executar limpeza: {str(e)}"
        )
    finally:
        session.close()


@router.get("/system/overview")
def get_audit_system_overview(current_user: UserModel = Depends(get_current_user)):
    """
    Retorna visão geral do sistema de audit trail.
    
    Apenas administradores podem acessar.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem acessar visão geral do sistema"
        )
    
    # Implementar lógica para buscar estatísticas globais
    # Por enquanto, retornar informações básicas
    return {
        "message": "Visão geral do sistema de audit trail",
        "active_hotels": "Implementar contagem",
        "total_logs": "Implementar contagem",
        "logs_today": "Implementar contagem",
        "storage_usage": "Implementar cálculo",
        "system_status": "active"
    }


@router.post("/manual-log")
def create_manual_audit_log(
    hotel_id: str,
    action: str,
    resource_type: str,
    description: str,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Cria um log de auditoria manual.
    
    Útil para ações que não são capturadas automaticamente.
    """
    session = SessionLocal()
    try:
        audit_service = AuditTrailService(session)
        
        # Validar permissão
        if current_user.role != "admin" and current_user.hotel_id != hotel_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão negada para criar log neste hotel"
            )
        
        # Criar log manual
        log = audit_service.log_action(
            hotel_id=hotel_id,
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role,
            action=action,
            resource_type=resource_type,
            description=description,
            resource_id=resource_id,
            details=details,
            status="SUCCESS"
        )
        
        session.commit()
        
        return {
            "message": "Log de auditoria criado com sucesso",
            "log_id": log.id,
            "created_at": log.timestamp
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar log: {str(e)}"
        )
    finally:
        session.close()
