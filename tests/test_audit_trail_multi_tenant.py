"""Testes para Audit Trail multi-tenant."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.infrastructure.persistence.sql.audit_trail_repository import AuditTrailService
from app.infrastructure.persistence.sql.audit_models import AuditLogModel, AuditLogRetentionModel
from app.infrastructure.persistence.sql.models import UserModel


class TestAuditTrailService:
    """Testes do serviço de audit trail com isolamento por hotel."""
    
    def setup_method(self):
        """Setup para cada teste."""
        self.mock_session = Mock(spec=Session)
        self.audit_service = AuditTrailService(self.mock_session)
        
        # Usuários de teste
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
        
        self.super_admin = UserModel(
            id="super-admin-789",
            email="superadmin@system.com",
            hotel_id=None,
            role="admin"
        )
    
    def test_log_action_creates_record_with_hotel_id(self):
        """Testa que log_action cria registro com hotel_id correto."""
        hotel_id = "test-hotel-123"
        
        # Mock do método _get_retention_config
        with patch.object(self.audit_service, '_get_retention_config') as mock_retention:
            mock_retention.return_value = self._create_mock_retention_config()
            
            # Mock do método _update_hotel_stats
            with patch.object(self.audit_service, '_update_hotel_stats'):
                result = self.audit_service.log_action(
                    hotel_id=hotel_id,
                    user_id="user-123",
                    user_email="user@test.com",
                    user_role="user",
                    action="CREATE",
                    resource_type="reservation",
                    description="Criou nova reserva",
                    resource_id="res-123",
                    details={"guest_name": "João"}
                )
        
        # Verificar que o audit log foi criado com hotel_id correto
        self.mock_session.add.assert_called_once()
        self.mock_session.flush.assert_called_once()
        
        # Capturar o AuditLogModel criado
        added_call = self.mock_session.add.call_args
        audit_log = added_call[0][0]
        
        assert audit_log.hotel_id == hotel_id
        assert audit_log.user_id == "user-123"
        assert audit_log.user_email == "user@test.com"
        assert audit_log.action == "CREATE"
        assert audit_log.resource_type == "reservation"
        assert audit_log.description == "Criou nova reserva"
        assert audit_log.resource_id == "res-123"
    
    def test_get_hotel_logs_enforces_permission(self):
        """Testa que get_hotel_logs respeita permissões por hotel."""
        hotel_id = "d03dbe9a-1812-46dd-8e8c-c8fedace48a0"
        
        # Usuário do Hotel Temp tentando acessar logs do Hotel Kelly
        with pytest.raises(PermissionError) as exc_info:
            self.audit_service.get_hotel_logs(hotel_id, self.user_temp)
        
        assert "não tem permissão para acessar logs" in str(exc_info.value)
    
    def test_admin_can_access_any_hotel_logs(self):
        """Testa que admin pode acessar logs de qualquer hotel."""
        hotel_id = "temp-hotel"
        
        # Mock da query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        self.mock_session.query.return_value = mock_query
        
        # Admin deve conseguir acessar
        result = self.audit_service.get_hotel_logs(hotel_id, self.user_kelly)
        
        # Verificar que query foi executada com hotel_id correto
        self.mock_session.query.assert_called_once_with(AuditLogModel)
        mock_query.filter.assert_called_once()
        
        # Capturar o filtro aplicado
        filter_call = mock_query.filter.call_args[0][0]
        # Verificar que filtra por hotel_id
        assert str(filter_call).find("hotel_id") != -1
    
    def test_super_admin_can_access_any_hotel_logs(self):
        """Testa que super admin pode acessar logs de qualquer hotel."""
        hotel_id = "any-hotel-id"
        
        # Mock da query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        self.mock_session.query.return_value = mock_query
        
        # Super admin deve conseguir acessar
        result = self.audit_service.get_hotel_logs(hotel_id, self.super_admin)
        
        # Verificar que query foi executada
        self.mock_session.query.assert_called_once_with(AuditLogModel)
    
    def test_get_user_activity_isolated_by_hotel(self):
        """Testa que get_user_activity é isolado por hotel."""
        hotel_id = "d03dbe9a-1812-46dd-8e8c-c8fedace48a0"
        user_email = "user@test.com"
        
        # Mock da query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        
        self.mock_session.query.return_value = mock_query
        
        # Buscar atividades
        result = self.audit_service.get_user_activity(hotel_id, self.user_kelly, user_email)
        
        # Verificar que query filtra por hotel_id E user_email
        self.mock_session.query.assert_called_once_with(AuditLogModel)
        
        # Capturar filtros aplicados
        filter_calls = mock_query.filter.call_args_list
        filter_conditions = [str(call[0][0]) for call in filter_calls]
        
        # Deve filtrar por hotel_id e user_email
        assert any("hotel_id" in condition for condition in filter_conditions)
        assert any("user_email" in condition for condition in filter_conditions)
    
    def test_get_resource_history_isolated_by_hotel(self):
        """Testa que get_resource_history é isolado por hotel."""
        hotel_id = "d03dbe9a-1812-46dd-8e8c-c8fedace48a0"
        resource_type = "reservation"
        resource_id = "res-123"
        
        # Mock da query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        
        self.mock_session.query.return_value = mock_query
        
        # Buscar histórico
        result = self.audit_service.get_resource_history(hotel_id, self.user_kelly, resource_type, resource_id)
        
        # Verificar que query filtra por hotel_id, resource_type e resource_id
        self.mock_session.query.assert_called_once_with(AuditLogModel)
        
        # Capturar filtros aplicados
        filter_calls = mock_query.filter.call_args_list
        filter_conditions = [str(call[0][0]) for call in filter_calls]
        
        # Deve filtrar por todos os três campos
        assert any("hotel_id" in condition for condition in filter_conditions)
        assert any("resource_type" in condition for condition in filter_conditions)
        assert any("resource_id" in condition for condition in filter_conditions)
    
    def test_get_hotel_statistics_isolated_by_hotel(self):
        """Testa que get_hotel_statistics é isolado por hotel."""
        hotel_id = "d03dbe9a-1812-46dd-8e8c-c8fedace48a0"
        
        # Mock das queries de contagem
        def mock_query_func(model):
            mock_query = Mock()
            
            if model == AuditLogModel:
                # Configurar diferentes retornos para diferentes queries
                def mock_filter(*args):
                    filter_str = str(args[0])
                    mock_query.count.return_value = 100  # total
                    
                    if "status == 'SUCCESS'" in filter_str:
                        mock_query.count.return_value = 90  # successful
                    elif "status.in_" in filter_str:
                        mock_query.count.return_value = 10  # failed
                    elif "group_by" in str(mock_query.group_by):
                        if "action" in str(mock_query.group_by):
                            mock_query.all.return_value = [("CREATE", 50), ("UPDATE", 30), ("DELETE", 20)]
                        elif "resource_type" in str(mock_query.group_by):
                            mock_query.all.return_value = [("reservation", 60), ("user", 25), ("room", 15)]
                        elif "user_email" in str(mock_query.group_by):
                            mock_query.all.return_value = [("user1@test.com", 40), ("user2@test.com", 30)]
                    return mock_query
                
                mock_query.filter.side_effect = mock_filter
                mock_query.order_by.return_value = mock_query
                mock_query.limit.return_value = mock_query
                mock_query.group_by.return_value = mock_query
                
            return mock_query
        
        self.mock_session.query.side_effect = mock_query_func
        
        # Buscar estatísticas
        result = self.audit_service.get_hotel_statistics(hotel_id, self.user_kelly)
        
        # Verificar que estatísticas retornam hotel_id correto
        assert result["hotel_id"] == hotel_id
        assert result["total_actions"] == 100
        assert result["successful_actions"] == 90
        assert result["failed_actions"] == 10
        assert result["success_rate"] == 90.0
    
    def test_cleanup_expired_logs_isolated_by_hotel(self):
        """Testa que cleanup_expired_logs é isolado por hotel."""
        hotel_id = "d03dbe9a-1812-46dd-8e8c-c8fedace48a0"
        
        # Mock de logs expirados
        expired_log = Mock(spec=AuditLogModel)
        expired_log.hotel_id = hotel_id
        
        # Mock da query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [expired_log]
        
        self.mock_session.query.return_value = mock_query
        
        # Limpar logs expirados
        result = self.audit_service.cleanup_expired_logs(hotel_id)
        
        # Verificar que filtra por hotel_id correto
        self.mock_session.query.assert_called_once_with(AuditLogModel)
        
        # Capturar filtro aplicado
        filter_call = mock_query.filter.call_args[0][0]
        filter_str = str(filter_call)
        
        # Deve filtrar por hotel_id e expires_at
        assert "hotel_id" in filter_str
        assert "expires_at" in filter_str
        
        # Verificar que apenas log do hotel correto foi deletado
        self.mock_session.delete.assert_called_once_with(expired_log)
        
        # Verificar retorno
        assert result == 1
    
    def test_sensitive_data_masking(self):
        """Testa que dados sensíveis são mascarados."""
        config = self._create_mock_retention_config()
        config.include_sensitive_data = "MASKED"
        
        # Dados sensíveis
        sensitive_details = {
            "password": "secret123",
            "token": "abc123token",
            "credit_card": "4111111111111111",
            "normal_field": "normal_value"
        }
        
        masked_details = self.audit_service._mask_sensitive_data(sensitive_details, config)
        
        # Verificar mascaramento
        assert masked_details["password"] == "***MASKED***"
        assert masked_details["token"] == "***MASKED***"
        assert masked_details["credit_card"] == "***MASKED***"
        assert masked_details["normal_field"] == "normal_value"
    
    def test_expiry_date_calculation(self):
        """Testa cálculo de data de expiração baseado na ação."""
        config = self._create_mock_retention_config()
        
        # Ação normal
        expiry = self.audit_service._calculate_expiry_date("CREATE", "SUCCESS", config)
        expected = datetime.utcnow() + timedelta(days=config.default_retention_days)
        assert abs((expiry - expected).total_seconds()) < 1  # Diferença < 1 segundo
        
        # Ação falha
        expiry = self.audit_service._calculate_expiry_date("CREATE", "FAILED", config)
        expected = datetime.utcnow() + timedelta(days=config.failed_action_retention_days)
        assert abs((expiry - expected).total_seconds()) < 1
        
        # Ação de autenticação
        expiry = self.audit_service._calculate_expiry_date("LOGIN", "SUCCESS", config)
        expected = datetime.utcnow() + timedelta(days=config.auth_action_retention_days)
        assert abs((expiry - expected).total_seconds()) < 1
    
    def _create_mock_retention_config(self):
        """Cria configuração de retenção mock."""
        config = Mock(spec=AuditLogRetentionModel)
        config.default_retention_days = 90
        config.failed_action_retention_days = 365
        config.auth_action_retention_days = 30
        config.include_sensitive_data = "MASKED"
        return config


class TestAuditTrailMiddleware:
    """Testes do middleware de audit trail."""
    
    def setup_method(self):
        """Setup para cada teste."""
        from app.interfaces.middleware.audit_trail_middleware import AuditTrailMiddleware
        self.middleware = AuditTrailMiddleware(app=None)
    
    def test_extract_request_info(self):
        """Testa extração de informações do request."""
        # Mock request
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url = Mock()
        mock_request.url.path = "/api/reservations"
        mock_request.url.query_params = {"test": "value"}
        mock_request.headers = {
            "user-agent": "Mozilla/5.0",
            "content-type": "application/json",
            "content-length": "1000"
        }
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.100"
        
        info = self.middleware._extract_request_info(mock_request)
        
        assert info["method"] == "POST"
        assert info["path"] == "/api/reservations"
        assert info["query_params"] == {"test": "value"}
        assert info["ip_address"] == "192.168.1.100"
        assert info["user_agent"] == "Mozilla/5.0"
        assert info["content_type"] == "application/json"
        assert info["content_length"] == "1000"
    
    def test_classify_action(self):
        """Testa classificação correta de ações."""
        # Mock request e response
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url = Mock()
        
        mock_response = Mock()
        mock_response.status_code = 201
        
        # Testar diferentes paths
        paths_and_expected = [
            ("/auth/login", ("LOGIN", "auth", None)),
            ("/auth/logout", ("LOGOUT", "auth", None)),
            ("/reservations", ("CREATE", "reservation", None)),
            ("/reservations/123", ("UPDATE", "reservation", "123")),
            ("/rooms", ("CREATE", "room", None)),
            ("/users", ("CREATE", "user", None)),
            ("/admin/users", ("ADMIN", "admin", None)),
            ("/whatsapp/webhook", ("WHATSAPPOT", "whatsapp", None)),
        ]
        
        for path, expected in paths_and_expected:
            mock_request.url.path = path
            result = self.middleware._classify_action(mock_request, mock_response)
            assert result == expected
    
    def test_should_log_action(self):
        """Testa lógica de quando fazer logging."""
        # Mock request e response
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url = Mock()
        mock_request.url.path = "/api/reservations"
        
        mock_response_success = Mock()
        mock_response_success.status_code = 201
        
        mock_response_error = Mock()
        mock_response_error.status_code = 400
        
        # Testar POST (deve logar)
        assert self.middleware._should_log_action(mock_request, mock_response_success, None) == True
        
        # Testar GET (não deve logar)
        mock_request.method = "GET"
        assert self.middleware._should_log_action(mock_request, mock_response_success, None) == False
        
        # Testar erro (deve logar mesmo GET)
        assert self.middleware._should_log_action(mock_request, mock_response_error, None) == True
        
        # Testar endpoint de auth (deve logar)
        mock_request.method = "POST"
        mock_request.url.path = "/auth/login"
        assert self.middleware._should_log_action(mock_request, mock_response_success, None) == True
        
        # Testar endpoint admin (deve logar)
        mock_request.url.path = "/admin/users"
        assert self.middleware._should_log_action(mock_request, mock_response_success, None) == True
    
    def test_determine_status(self):
        """Testa determinação de status baseado no response."""
        # Mock responses
        response_success = Mock()
        response_success.status_code = 200
        
        response_client_error = Mock()
        response_client_error.status_code = 400
        
        response_server_error = Mock()
        response_server_error.status_code = 500
        
        # Testar diferentes status codes
        assert self.middleware._determine_status(response_success) == "SUCCESS"
        assert self.middleware._determine_status(response_client_error) == "FAILED"
        assert self.middleware._determine_status(response_server_error) == "ERROR"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
