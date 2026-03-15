"""Rate Limiting middleware com isolamento por hotel."""
import time
import redis
from typing import Dict, Optional
from fastapi import Request, HTTPException, status
from app.interfaces.dependencies.auth import get_current_user
from app.infrastructure.persistence.sql.models import UserModel


class HotelRateLimiter:
    """Rate limiter que funciona por hotel individualmente."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_limits = {
            "global": {"requests": 1000, "window": 3600},  # 1000 requests/hora por hotel
            "auth": {"requests": 10, "window": 300},        # 10 login attempts/5min por hotel
            "api": {"requests": 500, "window": 3600},       # 500 API calls/hora por hotel
            "reservation": {"requests": 50, "window": 3600}, # 50 reservations/hora por hotel
            "whatsapp": {"requests": 100, "window": 3600},  # 100 WhatsApp msgs/hora por hotel
        }
    
    def _get_key(self, hotel_id: str, endpoint_type: str, identifier: str = None) -> str:
        """Gera chave Redis para rate limiting por hotel."""
        if identifier:
            return f"rate_limit:{hotel_id}:{endpoint_type}:{identifier}"
        return f"rate_limit:{hotel_id}:{endpoint_type}"
    
    def _get_hotel_id_from_user(self, user: UserModel) -> str:
        """Extrai hotel_id do usuário, com validação."""
        if not user.hotel_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário não associado a nenhum hotel para rate limiting"
            )
        return user.hotel_id
    
    def is_allowed(self, hotel_id: str, endpoint_type: str, identifier: str = None) -> Dict:
        """
        Verifica se request é permitido baseado no rate limit do hotel.
        
        Args:
            hotel_id: ID do hotel
            endpoint_type: Tipo de endpoint (global, auth, api, etc.)
            identifier: Identificador adicional (IP, user_id, etc.)
            
        Returns:
            Dict com informações sobre o rate limit
        """
        limits = self.default_limits.get(endpoint_type, self.default_limits["global"])
        key = self._get_key(hotel_id, endpoint_type, identifier)
        
        try:
            # Usar Redis INCR para contador atômico
            current_count = self.redis.incr(key)
            
            if current_count == 1:
                # Primeiro request, setar expiração
                self.redis.expire(key, limits["window"])
            
            # Calcular tempo restante
            ttl = self.redis.ttl(key)
            
            return {
                "allowed": current_count <= limits["requests"],
                "limit": limits["requests"],
                "remaining": max(0, limits["requests"] - current_count),
                "reset_time": int(time.time()) + ttl if ttl > 0 else 0,
                "current_count": current_count,
                "window": limits["window"]
            }
            
        except redis.RedisError:
            # Se Redis falhar, permitir request (fail open)
            return {
                "allowed": True,
                "limit": limits["requests"],
                "remaining": limits["requests"],
                "reset_time": 0,
                "current_count": 0,
                "window": limits["window"]
            }
    
    def check_rate_limit(self, endpoint_type: str, identifier: str = None):
        """
        Decorator/Função para verificar rate limit por hotel.
        
        Args:
            endpoint_type: Tipo de endpoint
            identifier: Identificador adicional (opcional)
        """
        def _check_limit(user: UserModel = Depends(get_current_user)):
            hotel_id = self._get_hotel_id_from_user(user)
            result = self.is_allowed(hotel_id, endpoint_type, identifier)
            
            if not result["allowed"]:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "hotel_id": hotel_id,
                        "limit": result["limit"],
                        "window": result["window"],
                        "reset_time": result["reset_time"],
                        "retry_after": result["reset_time"] - int(time.time())
                    }
                )
            
            return result
        
        return _check_limit
    
    def get_hotel_stats(self, hotel_id: str) -> Dict:
        """Retorna estatísticas de rate limit para um hotel."""
        stats = {}
        
        for endpoint_type in self.default_limits.keys():
            key = self._get_key(hotel_id, endpoint_type)
            try:
                current_count = int(self.redis.get(key) or 0)
                ttl = self.redis.ttl(key)
                limits = self.default_limits[endpoint_type]
                
                stats[endpoint_type] = {
                    "current_count": current_count,
                    "limit": limits["requests"],
                    "remaining": max(0, limits["requests"] - current_count),
                    "reset_time": int(time.time()) + ttl if ttl > 0 else 0,
                    "window": limits["window"]
                }
            except redis.RedisError:
                stats[endpoint_type] = {"error": "Redis unavailable"}
        
        return stats
    
    def reset_hotel_limits(self, hotel_id: str, endpoint_type: str = None):
        """
        Reseta rate limits para um hotel (admin only).
        
        Args:
            hotel_id: ID do hotel
            endpoint_type: Tipo específico (opcional, se None reseta todos)
        """
        if endpoint_type:
            key = self._get_key(hotel_id, endpoint_type)
            self.redis.delete(key)
        else:
            # Deletar todas as chaves do hotel
            pattern = f"rate_limit:{hotel_id}:*"
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)


# Instância global do rate limiter
_rate_limiter_instance: Optional[HotelRateLimiter] = None


def get_rate_limiter() -> HotelRateLimiter:
    """Retorna instância do rate limiter."""
    global _rate_limiter_instance
    
    if _rate_limiter_instance is None:
        try:
            # Tentar conectar ao Redis
            import os
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", 6379))
            
            redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Testar conexão
            redis_client.ping()
            _rate_limiter_instance = HotelRateLimiter(redis_client)
            
        except (redis.RedisError, ConnectionError):
            # Se Redis não estiver disponível, criar instância mock
            class MockRedis:
                def __init__(self):
                    self.counters = {}
                
                def incr(self, key):
                    self.counters[key] = self.counters.get(key, 0) + 1
                    return self.counters[key]
                
                def expire(self, key, seconds):
                    pass
                
                def ttl(self, key):
                    return 3600
                
                def get(self, key):
                    return str(self.counters.get(key, 0))
                
                def delete(self, *keys):
                    for key in keys:
                        self.counters.pop(key, None)
                
                def keys(self, pattern):
                    return [k for k in self.counters.keys() if pattern.replace("*", "") in k]
                
                def ping(self):
                    return True
            
            _rate_limiter_instance = HotelRateLimiter(MockRedis())
    
    return _rate_limiter_instance


# Funções de conveniência para uso nos endpoints
def check_api_rate_limit(identifier: str = None):
    """Verifica rate limit para API endpoints."""
    return get_rate_limiter().check_rate_limit("api", identifier)


def check_auth_rate_limit(identifier: str = None):
    """Verifica rate limit para endpoints de autenticação."""
    return get_rate_limiter().check_rate_limit("auth", identifier)


def check_reservation_rate_limit(identifier: str = None):
    """Verifica rate limit para endpoints de reservas."""
    return get_rate_limiter().check_rate_limit("reservation", identifier)


def check_whatsapp_rate_limit(identifier: str = None):
    """Verifica rate limit para endpoints WhatsApp."""
    return get_rate_limiter().check_rate_limit("whatsapp", identifier)


def check_global_rate_limit(identifier: str = None):
    """Verifica rate limit global."""
    return get_rate_limiter().check_rate_limit("global", identifier)
