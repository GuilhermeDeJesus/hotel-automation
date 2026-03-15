"""Middleware de Rate Limiting por Hotel para FastAPI."""
import time
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.interfaces.middleware.hotel_rate_limiter import get_rate_limiter
from app.interfaces.dependencies.auth import get_current_user_from_token
from app.infrastructure.persistence.sql.models import UserModel


class HotelRateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware que aplica rate limiting por hotel a todas as requests."""
    
    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.rate_limiter = get_rate_limiter()
        self.excluded_paths = {
            "/health", "/docs", "/openapi.json", "/favicon.ico"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting para paths excluídos
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Tentar extrair usuário do token (se existir)
        user = None
        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                user = get_current_user_from_token(token)
        except Exception:
            # Se falhar autenticação, continuar sem rate limiting por hotel
            pass
        
        # Se não tiver usuário, aplicar rate limiting global por IP
        if not user:
            return await self._apply_ip_rate_limit(request, call_next)
        
        # Se usuário não tiver hotel_id, bloquear
        if not user.hotel_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário não associado a nenhum hotel"
            )
        
        # Aplicar rate limiting por hotel
        return await self._apply_hotel_rate_limit(request, call_next, user)
    
    async def _apply_ip_rate_limit(self, request: Request, call_next: Callable) -> Response:
        """Aplica rate limiting baseado em IP (para requests não autenticadas)."""
        client_ip = self._get_client_ip(request)
        endpoint_type = self._get_endpoint_type(request.url.path)
        
        # Rate limiting mais restritivo para IPs não autenticados
        result = self.rate_limiter.is_allowed(
            hotel_id=f"ip:{client_ip}",
            endpoint_type=f"unauth_{endpoint_type}",
            identifier=client_ip
        )
        
        if not result["allowed"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "type": "ip_based",
                    "limit": result["limit"],
                    "retry_after": result["reset_time"] - int(time.time())
                }
            )
        
        response = await call_next(request)
        self._add_rate_limit_headers(response, result)
        return response
    
    async def _apply_hotel_rate_limit(self, request: Request, call_next: Callable, user: UserModel) -> Response:
        """Aplica rate limiting baseado no hotel do usuário."""
        endpoint_type = self._get_endpoint_type(request.url.path)
        identifier = f"user:{user.id}"
        
        result = self.rate_limiter.is_allowed(
            hotel_id=user.hotel_id,
            endpoint_type=endpoint_type,
            identifier=identifier
        )
        
        if not result["allowed"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "hotel_id": user.hotel_id,
                    "type": "hotel_based",
                    "limit": result["limit"],
                    "retry_after": result["reset_time"] - int(time.time())
                }
            )
        
        response = await call_next(request)
        self._add_rate_limit_headers(response, result)
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extrai IP real do cliente."""
        # Verificar headers de proxy
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else "unknown"
    
    def _get_endpoint_type(self, path: str) -> str:
        """Classifica o tipo de endpoint baseado no path."""
        if "/auth" in path or "/login" in path or "/register" in path:
            return "auth"
        elif "/reservations" in path:
            return "reservation"
        elif "/whatsapp" in path or "/webhook" in path:
            return "whatsapp"
        elif "/api" in path:
            return "api"
        else:
            return "global"
    
    def _add_rate_limit_headers(self, response: Response, result: dict):
        """Adiciona headers de rate limit à response."""
        response.headers["X-RateLimit-Limit"] = str(result["limit"])
        response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
        response.headers["X-RateLimit-Reset"] = str(result["reset_time"])
        response.headers["X-RateLimit-Window"] = str(result["window"])


class HotelRateLimitAdminMiddleware:
    """Middleware para administração de rate limits por hotel."""
    
    def __init__(self, rate_limiter=None):
        self.rate_limiter = rate_limiter or get_rate_limiter()
    
    def get_hotel_rate_stats(self, hotel_id: str, user: UserModel) -> dict:
        """Retorna estatísticas de rate limit para um hotel."""
        # Apenas admin ou mesmo hotel pode ver stats
        if user.role != "admin" and user.hotel_id != hotel_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão negada para ver estatísticas deste hotel"
            )
        
        return self.rate_limiter.get_hotel_stats(hotel_id)
    
    def reset_hotel_rate_limits(self, hotel_id: str, endpoint_type: str = None, user: UserModel = None):
        """Reseta rate limits para um hotel (admin only)."""
        if user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas administradores podem resetar rate limits"
            )
        
        self.rate_limiter.reset_hotel_limits(hotel_id, endpoint_type)
    
    def update_hotel_limits(self, hotel_id: str, new_limits: dict, user: UserModel = None):
        """Atualiza limites personalizados para um hotel (super admin only)."""
        if user.role != "admin" or user.hotel_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas super administradores podem atualizar limites"
            )
        
        # Implementar lógica para salvar limites personalizados
        # Por enquanto, usar os defaults
        pass
