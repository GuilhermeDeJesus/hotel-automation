"""Endpoints de administração de Rate Limiting por Hotel."""
from fastapi import APIRouter, Depends, HTTPException, status
from app.interfaces.middleware.rate_limit_middleware import HotelRateLimitAdminMiddleware
from app.interfaces.dependencies.auth import get_current_user
from app.infrastructure.persistence.sql.models import UserModel


router = APIRouter(prefix="/admin/rate-limits", tags=["Rate Limiting Admin"])
rate_limit_admin = HotelRateLimitAdminMiddleware()


@router.get("/hotels/{hotel_id}/stats")
def get_hotel_rate_stats(
    hotel_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retorna estatísticas de rate limit para um hotel específico.
    
    - Admin: pode ver stats de qualquer hotel
    - Outros: só podem ver stats do próprio hotel
    """
    try:
        stats = rate_limit_admin.get_hotel_rate_stats(hotel_id, current_user)
        return {
            "hotel_id": hotel_id,
            "stats": stats,
            "timestamp": int(time.time())
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar estatísticas: {str(e)}"
        )


@router.post("/hotels/{hotel_id}/reset")
def reset_hotel_rate_limits(
    hotel_id: str,
    endpoint_type: str = None,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Reseta rate limits para um hotel específico.
    
    Apenas administradores podem executar esta ação.
    
    - endpoint_type: opcional, se não informado reseta todos os tipos
    """
    try:
        rate_limit_admin.reset_hotel_rate_limits(hotel_id, endpoint_type, current_user)
        return {
            "message": "Rate limits resetados com sucesso",
            "hotel_id": hotel_id,
            "endpoint_type": endpoint_type or "todos",
            "reset_by": current_user.email
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao resetar rate limits: {str(e)}"
        )


@router.get("/hotels/{hotel_id}/current-usage")
def get_hotel_current_usage(
    hotel_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retorna uso atual de rate limits em tempo real.
    
    Útil para dashboard de monitoramento.
    """
    try:
        stats = rate_limit_admin.get_hotel_rate_stats(hotel_id, current_user)
        
        # Calcular percentuais de uso
        usage_summary = {}
        for endpoint, data in stats.items():
            if "error" not in data:
                usage_percent = (data["current_count"] / data["limit"]) * 100
                usage_summary[endpoint] = {
                    "current": data["current_count"],
                    "limit": data["limit"],
                    "remaining": data["remaining"],
                    "usage_percent": round(usage_percent, 2),
                    "reset_time": data["reset_time"],
                    "status": "warning" if usage_percent > 80 else "normal"
                }
        
        return {
            "hotel_id": hotel_id,
            "usage": usage_summary,
            "overall_status": "warning" if any(
                item["status"] == "warning" for item in usage_summary.values()
            ) else "normal"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar uso atual: {str(e)}"
        )


@router.get("/system/overview")
def get_system_rate_limit_overview(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retorna visão geral do sistema de rate limiting.
    
    Apenas administradores podem acessar.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem acessar visão geral do sistema"
        )
    
    try:
        # Implementar lógica para buscar estatísticas de todos os hotéis
        # Por enquanto, retornar informações básicas
        return {
            "message": "Visão geral do sistema de rate limiting",
            "active_hotels": "Implementar contagem de hotéis ativos",
            "total_requests": "Implementar contagem total",
            "rate_limiter_status": "active",
            "redis_status": "connected" if rate_limit_admin.rate_limiter.redis else "disconnected"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar visão geral: {str(e)}"
        )
