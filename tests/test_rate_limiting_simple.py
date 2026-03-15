"""Testes unitários simples para Rate Limiting multi-tenant."""
import pytest
import time
from unittest.mock import Mock


class MockRedis:
    """Mock Redis para testes."""
    
    def __init__(self):
        self.counters = {}
        self.expirations = {}
    
    def incr(self, key):
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]
    
    def expire(self, key, seconds):
        self.expirations[key] = time.time() + seconds
    
    def ttl(self, key):
        return 3600  # Sempre retorna 1 hora
    
    def get(self, key):
        return str(self.counters.get(key, 0))
    
    def delete(self, *keys):
        for key in keys:
            self.counters.pop(key, None)
    
    def keys(self, pattern):
        return [k for k in self.counters.keys() if pattern.replace("*", "") in k]
    
    def ping(self):
        return True


class MockUser:
    """Mock User para testes."""
    
    def __init__(self, id, email, hotel_id, role):
        self.id = id
        self.email = email
        self.hotel_id = hotel_id
        self.role = role


class SimpleRateLimiter:
    """Rate limper simplificado para testes."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.default_limits = {
            "global": {"requests": 1000, "window": 3600},
            "auth": {"requests": 10, "window": 300},
            "api": {"requests": 500, "window": 3600},
            "reservation": {"requests": 50, "window": 3600},
            "whatsapp": {"requests": 100, "window": 3600},
        }
    
    def _get_key(self, hotel_id: str, endpoint_type: str, identifier: str = None) -> str:
        if identifier:
            return f"rate_limit:{hotel_id}:{endpoint_type}:{identifier}"
        return f"rate_limit:{hotel_id}:{endpoint_type}"
    
    def is_allowed(self, hotel_id: str, endpoint_type: str, identifier: str = None) -> dict:
        limits = self.default_limits.get(endpoint_type, self.default_limits["global"])
        key = self._get_key(hotel_id, endpoint_type, identifier)
        
        try:
            current_count = self.redis.incr(key)
            
            if current_count == 1:
                self.redis.expire(key, limits["window"])
            
            ttl = self.redis.ttl(key)
            
            return {
                "allowed": current_count <= limits["requests"],
                "limit": limits["requests"],
                "remaining": max(0, limits["requests"] - current_count),
                "reset_time": int(time.time()) + ttl if ttl > 0 else 0,
                "current_count": current_count,
                "window": limits["window"]
            }
            
        except Exception:
            return {
                "allowed": True,
                "limit": limits["requests"],
                "remaining": limits["requests"],
                "reset_time": 0,
                "current_count": 0,
                "window": limits["window"]
            }


class TestRateLimitingStandalone:
    """Testes standalone de rate limiting multi-tenant."""
    
    def setup_method(self):
        """Setup para cada teste."""
        self.mock_redis = MockRedis()
        self.rate_limiter = SimpleRateLimiter(self.mock_redis)
        
        # Usuários de teste
        self.user_kelly = MockUser(
            id="user-kelly-123",
            email="admin@kelly.com",
            hotel_id="d03dbe9a-1812-46dd-8e8c-c8fedace48a0",
            role="admin"
        )
        
        self.user_temp = MockUser(
            id="user-temp-456", 
            email="user@temp.com",
            hotel_id="temp-hotel",
            role="user"
        )
    
    def test_different_hotels_independent_limits(self):
        """Testa que hotéis diferentes têm limites independentes."""
        hotel_kelly = "d03dbe9a-1812-46dd-8e8c-c8fedace48a0"
        hotel_temp = "temp-hotel"
        
        # Fazer requests do Hotel Kelly
        result_kelly_1 = self.rate_limiter.is_allowed(hotel_kelly, "api")
        result_kelly_2 = self.rate_limiter.is_allowed(hotel_kelly, "api")
        
        # Fazer requests do Hotel Temp
        result_temp_1 = self.rate_limiter.is_allowed(hotel_temp, "api")
        result_temp_2 = self.rate_limiter.is_allowed(hotel_temp, "api")
        result_temp_3 = self.rate_limiter.is_allowed(hotel_temp, "api")
        
        # Verificar contadores independentes
        assert result_kelly_1["current_count"] == 1
        assert result_kelly_2["current_count"] == 2
        
        assert result_temp_1["current_count"] == 1
        assert result_temp_2["current_count"] == 2
        assert result_temp_3["current_count"] == 3
        
        # Verificar que são independentes
        assert result_kelly_2["current_count"] != result_temp_3["current_count"]
    
    def test_rate_limit_enforcement(self):
        """Testa que rate limit é aplicado corretamente."""
        hotel_id = "test-hotel-123"
        
        # Fazer requests até o limite (auth: 10 requests)
        results = []
        for i in range(12):  # 2 requests acima do limite
            result = self.rate_limiter.is_allowed(hotel_id, "auth")
            results.append(result)
        
        # Verificar que os primeiros 10 foram permitidos
        for i in range(10):
            assert results[i]["allowed"], f"Request {i+1} deveria ser permitido"
        
        # Verificar que os últimos 2 foram bloqueados
        for i in range(10, 12):
            assert not results[i]["allowed"], f"Request {i+1} deveria ser bloqueado"
        
        # Verificar contadores
        assert results[9]["current_count"] == 10
        assert results[9]["remaining"] == 0
        assert results[10]["current_count"] == 11
        assert results[10]["remaining"] == 0
    
    def test_different_endpoint_limits(self):
        """Testa que diferentes endpoints têm limites diferentes."""
        hotel_id = "test-hotel-123"
        
        # Testar diferentes tipos de endpoints
        auth_result = self.rate_limiter.is_allowed(hotel_id, "auth")
        api_result = self.rate_limiter.is_allowed(hotel_id, "api")
        reservation_result = self.rate_limiter.is_allowed(hotel_id, "reservation")
        whatsapp_result = self.rate_limiter.is_allowed(hotel_id, "whatsapp")
        global_result = self.rate_limiter.is_allowed(hotel_id, "global")
        
        # Verificar limites diferentes
        assert auth_result["limit"] == 10      # auth: 10/5min
        assert api_result["limit"] == 500     # api: 500/hora
        assert reservation_result["limit"] == 50  # reservation: 50/hora
        assert whatsapp_result["limit"] == 100  # whatsapp: 100/hora
        assert global_result["limit"] == 1000  # global: 1000/hora
    
    def test_hotel_isolation_with_identifiers(self):
        """Testa isolamento usando identificadores (usuários específicos)."""
        hotel_id = "test-hotel-123"
        
        # Requests de usuários diferentes no mesmo hotel
        user1_result = self.rate_limiter.is_allowed(hotel_id, "api", "user-1")
        user2_result = self.rate_limiter.is_allowed(hotel_id, "api", "user-2")
        user1_again = self.rate_limiter.is_allowed(hotel_id, "api", "user-1")
        
        # Verificar que cada usuário tem seu próprio contador
        assert user1_result["current_count"] == 1
        assert user2_result["current_count"] == 1
        assert user1_again["current_count"] == 2  # user-1 agora tem 2 requests
    
    def test_redis_keys_structure(self):
        """Testa estrutura das chaves Redis."""
        hotel_id = "test-hotel-123"
        endpoint_type = "api"
        identifier = "user-123"
        
        # Testar chave sem identificador
        key1 = self.rate_limiter._get_key(hotel_id, endpoint_type)
        assert key1 == f"rate_limit:{hotel_id}:{endpoint_type}"
        
        # Testar chave com identificador
        key2 = self.rate_limiter._get_key(hotel_id, endpoint_type, identifier)
        assert key2 == f"rate_limit:{hotel_id}:{endpoint_type}:{identifier}"
        
        # Verificar que são diferentes
        assert key1 != key2
    
    def test_rate_limit_headers_info(self):
        """Testa informações retornadas para headers HTTP."""
        hotel_id = "test-hotel-123"
        
        result = self.rate_limiter.is_allowed(hotel_id, "api")
        
        # Verificar campos necessários para headers
        assert "limit" in result
        assert "remaining" in result
        assert "reset_time" in result
        assert "window" in result
        assert "current_count" in result
        assert "allowed" in result
        
        # Verificar tipos
        assert isinstance(result["limit"], int)
        assert isinstance(result["remaining"], int)
        assert isinstance(result["reset_time"], int)
        assert isinstance(result["window"], int)
        assert isinstance(result["current_count"], int)
        assert isinstance(result["allowed"], bool)
    
    def test_concurrent_requests_simulation(self):
        """Testa simulação de requests concorrentes."""
        hotel_id = "test-hotel-123"
        
        # Simular múltiplos requests simultâneos
        results = []
        for i in range(5):
            result = self.rate_limiter.is_allowed(hotel_id, "api")
            results.append(result)
        
        # Verificar que todos foram permitidos (abaixo do limite)
        for result in results:
            assert result["allowed"]
        
        # Verificar que o contador incrementou corretamente
        assert results[0]["current_count"] == 1
        assert results[4]["current_count"] == 5
    
    def test_rate_limit_reset_simulation(self):
        """Testa simulação de reset de rate limit."""
        hotel_id = "test-hotel-123"
        
        # Fazer alguns requests
        self.rate_limiter.is_allowed(hotel_id, "api")
        self.rate_limiter.is_allowed(hotel_id, "api")
        
        # Verificar contador
        key = self.rate_limiter._get_key(hotel_id, "api")
        assert self.mock_redis.counters[key] == 2
        
        # Resetar manualmente
        self.mock_redis.delete(key)
        
        # Verificar que contador foi resetado
        assert self.mock_redis.counters.get(key) is None
        
        # Fazer novo request
        result = self.rate_limiter.is_allowed(hotel_id, "api")
        assert result["current_count"] == 1
        assert result["remaining"] == 499  # 500 - 1
    
    def test_hotel_specific_statistics(self):
        """Testa estatísticas específicas por hotel."""
        hotel_kelly = "d03dbe9a-1812-46dd-8e8c-c8fedace48a0"
        hotel_temp = "temp-hotel"
        
        # Fazer requests para diferentes hotéis
        for i in range(5):
            self.rate_limiter.is_allowed(hotel_kelly, "api")
            self.rate_limiter.is_allowed(hotel_temp, "auth")
        
        # Verificar contadores por hotel
        kelly_api_key = self.rate_limiter._get_key(hotel_kelly, "api")
        temp_auth_key = self.rate_limiter._get_key(hotel_temp, "auth")
        
        assert self.mock_redis.counters[kelly_api_key] == 5
        assert self.mock_redis.counters[temp_auth_key] == 5
        
        # Verificar que não há cruzamento
        kelly_auth_key = self.rate_limiter._get_key(hotel_kelly, "auth")
        temp_api_key = self.rate_limiter._get_key(hotel_temp, "api")
        
        assert self.mock_redis.counters.get(kelly_auth_key) is None
        assert self.mock_redis.counters.get(temp_api_key) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
