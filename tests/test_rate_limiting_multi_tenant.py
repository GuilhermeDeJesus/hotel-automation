"""Testes para Rate Limiting multi-tenant."""
import pytest
import time
from unittest.mock import Mock, patch
from app.interfaces.middleware.hotel_rate_limiter import HotelRateLimiter, get_rate_limiter
from app.infrastructure.persistence.sql.models import UserModel


class TestHotelRateLimiter:
    """Testes do rate limiter por hotel."""
    
    def setup_method(self):
        """Setup para cada teste."""
        self.mock_redis = Mock()
        self.rate_limiter = HotelRateLimiter(self.mock_redis)
        
        # Usuário de teste
        self.user_kelly = UserModel(
            id="user-kelly-123",
            email="admin@kelly.com",
            hotel_id="d03dbe9a-1812-46dd-8e8c-c8fedace48a0",
            role="admin"
        )
        
        self.user_temp = UserModel(
            id="user-temp-456", 
            email="user@temp.com",
            hotel_id="temp-hotel",
            role="user"
        )
    
    def test_different_hotels_have_independent_limits(self):
        """Testa que hotéis diferentes têm limites independentes."""
        hotel_kelly = "d03dbe9a-1812-46dd-8e8c-c8fedace48a0"
        hotel_temp = "temp-hotel"
        
        # Configurar mock para retornar contadores diferentes
        def mock_incr(key):
            if "d03dbe9a-1812-46dd-8e8c-c8fedace48a0" in key:
                return 5  # Kelly: 5 requests
            elif "temp-hotel" in key:
                return 15  # Temp: 15 requests
            return 1
        
        self.mock_redis.incr.side_effect = mock_incr
        self.mock_redis.ttl.return_value = 300
        self.mock_redis.get.return_value = "10"
        
        # Verificar limites do Hotel Kelly
        result_kelly = self.rate_limiter.is_allowed(hotel_kelly, "api")
        assert result_kelly["current_count"] == 5
        assert result_kelly["remaining"] == 495  # 500 - 5
        
        # Verificar limites do Hotel Temp
        result_temp = self.rate_limiter.is_allowed(hotel_temp, "api")
        assert result_temp["current_count"] == 15
        assert result_temp["remaining"] == 485  # 500 - 15
        
        # Verificar que são independentes
        assert result_kelly["current_count"] != result_temp["current_count"]
    
    def test_rate_limit_enforced_per_hotel(self):
        """Testa que rate limit é aplicado por hotel individualmente."""
        hotel_id = "test-hotel-123"
        endpoint_type = "auth"
        
        # Configurar mock para simular limite atingido
        self.mock_redis.incr.return_value = 11  # Acima do limite de 10
        self.mock_redis.ttl.return_value = 300
        
        result = self.rate_limiter.is_allowed(hotel_id, endpoint_type)
        
        assert not result["allowed"]
        assert result["limit"] == 10
        assert result["remaining"] == 0
        assert result["current_count"] == 11
    
    def test_rate_limit_not_exceeded(self):
        """Testa comportamento quando rate limit não é excedido."""
        hotel_id = "test-hotel-123"
        endpoint_type = "api"
        
        # Configurar mock para simular abaixo do limite
        self.mock_redis.incr.return_value = 5  # Abaixo do limite de 500
        self.mock_redis.ttl.return_value = 300
        
        result = self.rate_limiter.is_allowed(hotel_id, endpoint_type)
        
        assert result["allowed"]
        assert result["limit"] == 500
        assert result["remaining"] == 495  # 500 - 5
        assert result["current_count"] == 5
    
    def test_different_endpoint_types_have_different_limits(self):
        """Testa que diferentes endpoints têm limites diferentes."""
        hotel_id = "test-hotel-123"
        
        # Configurar mock
        self.mock_redis.incr.return_value = 1
        self.mock_redis.ttl.return_value = 300
        
        # Testar diferentes tipos de endpoints
        auth_result = self.rate_limiter.is_allowed(hotel_id, "auth")
        api_result = self.rate_limiter.is_allowed(hotel_id, "api")
        reservation_result = self.rate_limiter.is_allowed(hotel_id, "reservation")
        
        # Verificar limites diferentes
        assert auth_result["limit"] == 10      # auth: 10/5min
        assert api_result["limit"] == 500     # api: 500/hora
        assert reservation_result["limit"] == 50  # reservation: 50/hora
    
    def test_redis_failure_fails_open(self):
        """Testa que falha no Redis permite requests (fail open)."""
        hotel_id = "test-hotel-123"
        
        # Configurar mock para levantar exceção
        self.mock_redis.incr.side_effect = Exception("Redis connection failed")
        
        result = self.rate_limiter.is_allowed(hotel_id, "api")
        
        # Deve permitir mesmo com Redis falhando
        assert result["allowed"]
        assert result["limit"] == 500
        assert result["remaining"] == 500
        assert result["current_count"] == 0
    
    def test_user_without_hotel_blocked(self):
        """Testa que usuário sem hotel é bloqueado."""
        user_no_hotel = UserModel(
            id="user-no-hotel",
            email="nohotel@test.com",
            hotel_id=None,  # Sem hotel
            role="user"
        )
        
        with pytest.raises(Exception) as exc_info:
            self.rate_limiter._get_hotel_id_from_user(user_no_hotel)
        
        assert "não associado a nenhum hotel" in str(exc_info.value)
    
    def test_hotel_stats_isolation(self):
        """Testa que estatísticas são isoladas por hotel."""
        hotel_kelly = "d03dbe9a-1812-46dd-8e8c-c8fedace48a0"
        hotel_temp = "temp-hotel"
        
        # Configurar mocks para retornar dados diferentes
        def mock_get(key):
            if "d03dbe9a-1812-46dd-8e8c-c8fedace48a0:api" in key:
                return "10"
            elif "temp-hotel:api" in key:
                return "25"
            return "5"
        
        def mock_ttl(key):
            return 300
        
        def mock_keys(pattern):
            if "d03dbe9a-1812-46dd-8e8c-c8fedace48a0" in pattern:
                return ["rate_limit:d03dbe9a-1812-46dd-8e8c-c8fedace48a0:api", "rate_limit:d03dbe9a-1812-46dd-8e8c-c8fedace48a0:auth"]
            elif "temp-hotel" in pattern:
                return ["rate_limit:temp-hotel:api", "rate_limit:temp-hotel:auth"]
            return []
        
        self.mock_redis.get.side_effect = mock_get
        self.mock_redis.ttl.side_effect = mock_ttl
        self.mock_redis.keys.side_effect = mock_keys
        
        # Buscar estatísticas de cada hotel
        kelly_stats = self.rate_limiter.get_hotel_stats(hotel_kelly)
        temp_stats = self.rate_limiter.get_hotel_stats(hotel_temp)
        
        # Verificar que são diferentes
        assert kelly_stats["api"]["current_count"] == 10
        assert temp_stats["api"]["current_count"] == 25
    
    def test_reset_hotel_limits_isolation(self):
        """Testa que reset de limites afeta apenas o hotel alvo."""
        hotel_kelly = "d03dbe9a-1812-46dd-8e8c-c8fedace48a0"
        hotel_temp = "temp-hotel"
        
        deleted_keys = []
        
        def mock_delete(*keys):
            nonlocal deleted_keys
            deleted_keys.extend(keys)
        
        self.mock_redis.delete.side_effect = mock_delete
        self.mock_redis.keys.return_value = [
            "rate_limit:d03dbe9a-1812-46dd-8e8c-c8fedace48a0:api",
            "rate_limit:d03dbe9a-1812-46dd-8e8c-c8fedace48a0:auth",
            "rate_limit:temp-hotel:api",
            "rate_limit:temp-hotel:auth"
        ]
        
        # Resetar apenas Hotel Kelly
        self.rate_limiter.reset_hotel_limits(hotel_kelly, "api")
        
        # Verificar que apenas chaves do Kelly foram deletadas
        assert any("d03dbe9a-1812-46dd-8e8c-c8fedace48a0:api" in key for key in deleted_keys)
        assert not any("temp-hotel" in key for key in deleted_keys)


class TestRateLimiterIntegration:
    """Testes de integração do rate limiter."""
    
    def test_get_rate_limiter_returns_instance(self):
        """Testa que get_rate_limiter retorna instância válida."""
        rate_limiter = get_rate_limiter()
        
        assert rate_limiter is not None
        assert hasattr(rate_limiter, 'is_allowed')
        assert hasattr(rate_limiter, 'default_limits')
    
    @patch('redis.Redis')
    def test_redis_connection_success(self, mock_redis_class):
        """Testa conexão bem-sucedida ao Redis."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis_class.return_value = mock_client
        
        # Limpar cache para forçar nova instância
        import app.interfaces.middleware.hotel_rate_limiter
        app.interfaces.middleware.hotel_rate_limiter._rate_limiter_instance = None
        
        rate_limiter = get_rate_limiter()
        
        assert rate_limiter.redis == mock_client
        mock_client.ping.assert_called_once()
    
    @patch('redis.Redis')
    def test_redis_connection_failure_creates_mock(self, mock_redis_class):
        """Teste que falha na conexão cria mock Redis."""
        mock_redis_class.side_effect = Exception("Connection failed")
        
        # Limpar cache para forçar nova instância
        import app.interfaces.middleware.hotel_rate_limiter
        app.interfaces.middleware.hotel_rate_limiter._rate_limiter_instance = None
        
        rate_limiter = get_rate_limiter()
        
        # Deve criar instância com MockRedis
        assert hasattr(rate_limiter.redis, 'counters')  # Atributo do MockRedis


class TestRateLimitMiddleware:
    """Testes do middleware de rate limiting."""
    
    def setup_method(self):
        """Setup para cada teste."""
        from app.interfaces.middleware.rate_limit_middleware import HotelRateLimitMiddleware
        self.middleware = HotelRateLimitMiddleware(app=None)
    
    def test_classify_endpoint_types(self):
        """Testa classificação correta de endpoints."""
        # Testar endpoints de autenticação
        assert self.middleware._get_endpoint_type("/auth/login") == "auth"
        assert self.middleware._get_endpoint_type("/auth/register") == "auth"
        
        # Testar endpoints de reservas
        assert self.middleware._get_endpoint_type("/reservations") == "reservation"
        assert self.middleware._get_endpoint_type("/reservations/123") == "reservation"
        
        # Testar endpoints WhatsApp
        assert self.middleware._get_endpoint_type("/whatsapp/webhook") == "whatsapp"
        
        # Testar endpoints genéricos
        assert self.middleware._get_endpoint_type("/api/rooms") == "api"
        assert self.middleware._get_endpoint_type("/unknown") == "global"
    
    def test_client_ip_extraction(self):
        """Testa extração correta de IP."""
        # Mock request
        mock_request = Mock()
        
        # Testar X-Forwarded-For
        mock_request.headers = {"x-forwarded-for": "192.168.1.100, 10.0.0.1"}
        assert self.middleware._get_client_ip(mock_request) == "192.168.1.100"
        
        # Testar X-Real-IP
        mock_request.headers = {"x-real-ip": "192.168.1.200"}
        assert self.middleware._get_client_ip(mock_request) == "192.168.1.200"
        
        # Testar IP direto
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.300"
        assert self.middleware._get_client_ip(mock_request) == "192.168.1.300"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
