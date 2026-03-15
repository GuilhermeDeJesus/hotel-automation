"""Testes simples para Audit Trail multi-tenant."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock


class MockUser:
    """Mock User para testes."""
    
    def __init__(self, id, email, hotel_id, role):
        self.id = id
        self.email = email
        self.hotel_id = hotel_id
        self.role = role


class MockAuditLog:
    """Mock AuditLog para testes."""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 'test-id')
        self.hotel_id = kwargs.get('hotel_id')
        self.user_id = kwargs.get('user_id')
        self.user_email = kwargs.get('user_email')
        self.user_role = kwargs.get('user_role')
        self.action = kwargs.get('action')
        self.resource_type = kwargs.get('resource_type')
        self.resource_id = kwargs.get('resource_id')
        self.description = kwargs.get('description')
        self.timestamp = kwargs.get('timestamp', datetime.utcnow())
        self.status = kwargs.get('status', 'SUCCESS')


class MockSession:
    """Mock Session para testes."""
    
    def __init__(self):
        self.added_items = []
        self.deleted_items = []
        self.committed = False
    
    def add(self, item):
        self.added_items.append(item)
    
    def delete(self, item):
        self.deleted_items.append(item)
    
    def commit(self):
        self.committed = True
    
    def rollback(self):
        self.committed = False


class SimpleAuditTrailService:
    """Serviço de audit trail simplificado para testes."""
    
    def __init__(self, session):
        self.session = session
        self.logs = []
    
    def log_action(self, hotel_id, user_id, user_email, user_role, action, resource_type, 
                   description, resource_id=None, details=None, status="SUCCESS"):
        """Registra uma ação no audit trail."""
        audit_log = MockAuditLog(
            hotel_id=hotel_id,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            status=status
        )
        
        self.session.add(audit_log)
        self.logs.append(audit_log)
        
        return audit_log
    
    def get_hotel_logs(self, hotel_id, user, limit=100, offset=0):
        """Busca logs de um hotel específico com validação de permissão."""
        self._validate_log_access(hotel_id, user)
        
        # Filtrar logs por hotel_id
        hotel_logs = [log for log in self.logs if log.hotel_id == hotel_id]
        
        # Aplicar paginação
        paginated_logs = hotel_logs[offset:offset + limit]
        
        return paginated_logs
    
    def get_user_activity(self, hotel_id, user, target_user_email, days=30):
        """Busca atividades de um usuário específico no hotel."""
        self._validate_log_access(hotel_id, user)
        
        # Filtrar por hotel e usuário
        start_date = datetime.utcnow() - timedelta(days=days)
        user_logs = [
            log for log in self.logs 
            if log.hotel_id == hotel_id 
            and log.user_email == target_user_email
            and log.timestamp >= start_date
        ]
        
        return user_logs
    
    def get_resource_history(self, hotel_id, user, resource_type, resource_id):
        """Busca histórico de alterações de um recurso."""
        self._validate_log_access(hotel_id, user)
        
        # Filtrar por hotel, tipo e ID do recurso
        resource_logs = [
            log for log in self.logs 
            if log.hotel_id == hotel_id 
            and log.resource_type == resource_type
            and log.resource_id == resource_id
        ]
        
        return resource_logs
    
    def get_hotel_statistics(self, hotel_id, user, days=30):
        """Retorna estatísticas de auditoria para um hotel."""
        self._validate_log_access(hotel_id, user)
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Filtrar logs do período
        period_logs = [
            log for log in self.logs 
            if log.hotel_id == hotel_id and log.timestamp >= start_date
        ]
        
        # Calcular estatísticas
        total_logs = len(period_logs)
        successful_logs = len([log for log in period_logs if log.status == "SUCCESS"])
        failed_logs = len([log for log in period_logs if log.status in ["FAILED", "ERROR"]])
        
        # Contar por ação
        action_counts = {}
        for log in period_logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1
        
        # Contar por recurso
        resource_counts = {}
        for log in period_logs:
            resource_counts[log.resource_type] = resource_counts.get(log.resource_type, 0) + 1
        
        # Contar por usuário
        user_counts = {}
        for log in period_logs:
            user_counts[log.user_email] = user_counts.get(log.user_email, 0) + 1
        
        return {
            "hotel_id": hotel_id,
            "period_days": days,
            "total_actions": total_logs,
            "successful_actions": successful_logs,
            "failed_actions": failed_logs,
            "success_rate": round((successful_logs / total_logs * 100) if total_logs > 0 else 0, 2),
            "action_counts": action_counts,
            "resource_counts": resource_counts,
            "user_counts": user_counts,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _validate_log_access(self, hotel_id, user):
        """Valida se usuário pode acessar logs do hotel."""
        if user.role != "admin" and user.hotel_id != hotel_id:
            raise PermissionError(f"Usuário {user.email} não tem permissão para acessar logs do hotel {hotel_id}")


class TestAuditTrailSimple:
    """Testes simples de audit trail multi-tenant."""
    
    def setup_method(self):
        """Setup para cada teste."""
        self.mock_session = MockSession()
        self.audit_service = SimpleAuditTrailService(self.mock_session)
        
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
        
        self.super_admin = MockUser(
            id="super-admin-789",
            email="superadmin@system.com",
            hotel_id=None,
            role="admin"
        )
    
    def test_log_action_creates_record_with_hotel_id(self):
        """Testa que log_action cria registro com hotel_id correto."""
        hotel_id = "test-hotel-123"
        
        result = self.audit_service.log_action(
            hotel_id=hotel_id,
            user_id="user-123",
            user_email="user@test.com",
            user_role="user",
            action="CREATE",
            resource_type="reservation",
            description="Criou nova reserva",
            resource_id="res-123"
        )
        
        # Verificar que o audit log foi criado
        assert result.hotel_id == hotel_id
        assert result.user_id == "user-123"
        assert result.user_email == "user@test.com"
        assert result.action == "CREATE"
        assert result.resource_type == "reservation"
        assert result.description == "Criou nova reserva"
        assert result.resource_id == "res-123"
        
        # Verificar que foi adicionado à sessão
        assert len(self.mock_session.added_items) == 1
        assert self.mock_session.added_items[0] == result
    
    def test_get_hotel_logs_enforces_permission(self):
        """Testa que get_hotel_logs respeita permissões por hotel."""
        hotel_id = "d03dbe9a-1812-46dd-8e8c-c8fedace48a0"
        
        # Criar alguns logs
        self.audit_service.log_action(hotel_id, "user-1", "user1@test.com", "user", "CREATE", "reservation", "Log 1")
        self.audit_service.log_action(hotel_id, "user-2", "user2@test.com", "user", "UPDATE", "reservation", "Log 2")
        
        # Usuário do Hotel Temp tentando acessar logs do Hotel Kelly
        with pytest.raises(PermissionError) as exc_info:
            self.audit_service.get_hotel_logs(hotel_id, self.user_temp)
        
        assert "não tem permissão para acessar logs" in str(exc_info.value)
    
    def test_admin_can_access_any_hotel_logs(self):
        """Testa que admin pode acessar logs de qualquer hotel."""
        hotel_id = "temp-hotel"
        
        # Criar logs no Hotel Temp
        self.audit_service.log_action(hotel_id, "user-temp", "user@temp.com", "user", "CREATE", "reservation", "Log Temp 1")
        self.audit_service.log_action(hotel_id, "user-temp", "user@temp.com", "user", "UPDATE", "reservation", "Log Temp 2")
        
        # Admin do Hotel Kelly deve conseguir acessar logs do Hotel Temp
        result = self.audit_service.get_hotel_logs(hotel_id, self.user_kelly)
        
        # Verificar que retornou os logs corretos
        assert len(result) == 2
        assert all(log.hotel_id == hotel_id for log in result)
    
    def test_super_admin_can_access_any_hotel_logs(self):
        """Testa que super admin pode acessar logs de qualquer hotel."""
        hotel_id = "any-hotel-id"
        
        # Criar logs
        self.audit_service.log_action(hotel_id, "user-any", "user@any.com", "user", "CREATE", "reservation", "Log Any")
        
        # Super admin deve conseguir acessar
        result = self.audit_service.get_hotel_logs(hotel_id, self.super_admin)
        
        # Verificar que retornou os logs
        assert len(result) == 1
        assert result[0].hotel_id == hotel_id
    
    def test_get_user_activity_isolated_by_hotel(self):
        """Testa que get_user_activity é isolado por hotel."""
        hotel_kelly = "d03dbe9a-1812-46dd-8e8c-c8fedace48a0"
        hotel_temp = "temp-hotel"
        user_email = "user@test.com"
        
        # Criar logs em hotéis diferentes para o mesmo usuário
        self.audit_service.log_action(hotel_kelly, "user-123", user_email, "user", "CREATE", "reservation", "Log Kelly")
        self.audit_service.log_action(hotel_temp, "user-456", user_email, "user", "CREATE", "reservation", "Log Temp")
        
        # Buscar atividades no Hotel Kelly
        result = self.audit_service.get_user_activity(hotel_kelly, self.user_kelly, user_email)
        
        # Deve retornar apenas logs do Hotel Kelly
        assert len(result) == 1
        assert result[0].hotel_id == hotel_kelly
        assert result[0].user_email == user_email
    
    def test_get_resource_history_isolated_by_hotel(self):
        """Testa que get_resource_history é isolado por hotel."""
        hotel_kelly = "d03dbe9a-1812-46dd-8e8c-c8fedace48a0"
        hotel_temp = "temp-hotel"
        resource_type = "reservation"
        resource_id = "res-123"
        
        # Criar logs para o mesmo recurso em hotéis diferentes
        self.audit_service.log_action(hotel_kelly, "user-1", "user1@test.com", "user", "CREATE", resource_type, "Log Kelly", resource_id)
        self.audit_service.log_action(hotel_temp, "user-2", "user2@test.com", "user", "UPDATE", resource_type, "Log Temp", resource_id)
        
        # Buscar histórico no Hotel Kelly
        result = self.audit_service.get_resource_history(hotel_kelly, self.user_kelly, resource_type, resource_id)
        
        # Deve retornar apenas logs do Hotel Kelly
        assert len(result) == 1
        assert result[0].hotel_id == hotel_kelly
        assert result[0].resource_type == resource_type
        assert result[0].resource_id == resource_id
    
    def test_get_hotel_statistics_isolated_by_hotel(self):
        """Testa que get_hotel_statistics é isolado por hotel."""
        hotel_kelly = "d03dbe9a-1812-46dd-8e8c-c8fedace48a0"
        hotel_temp = "temp-hotel"
        
        # Criar logs em hotéis diferentes
        self.audit_service.log_action(hotel_kelly, "user-1", "user1@kelly.com", "user", "CREATE", "reservation", "Log Kelly 1")
        self.audit_service.log_action(hotel_kelly, "user-2", "user2@kelly.com", "user", "UPDATE", "reservation", "Log Kelly 2")
        self.audit_service.log_action(hotel_temp, "user-3", "user3@temp.com", "user", "CREATE", "reservation", "Log Temp 1")
        
        # Buscar estatísticas do Hotel Kelly
        result = self.audit_service.get_hotel_statistics(hotel_kelly, self.user_kelly)
        
        # Verificar que estatísticas são apenas do Hotel Kelly
        assert result["hotel_id"] == hotel_kelly
        assert result["total_actions"] == 2
        assert result["successful_actions"] == 2
        assert result["failed_actions"] == 0
        assert result["success_rate"] == 100.0
        
        # Verificar contadores
        assert "CREATE" in result["action_counts"]
        assert "UPDATE" in result["action_counts"]
        assert result["action_counts"]["CREATE"] == 1
        assert result["action_counts"]["UPDATE"] == 1
        
        # Verificar usuários
        assert "user1@kelly.com" in result["user_counts"]
        assert "user2@kelly.com" in result["user_counts"]
        assert "user3@temp.com" not in result["user_counts"]
    
    def test_different_hotels_independent_logs(self):
        """Testa que logs de hotéis diferentes são completamente independentes."""
        hotel_kelly = "d03dbe9a-1812-46dd-8e8c-c8fedace48a0"
        hotel_temp = "temp-hotel"
        
        # Criar logs em ambos os hotéis
        for i in range(5):
            self.audit_service.log_action(hotel_kelly, f"user-kelly-{i}", f"user{i}@kelly.com", "user", "CREATE", "reservation", f"Kelly Log {i}")
            self.audit_service.log_action(hotel_temp, f"user-temp-{i}", f"user{i}@temp.com", "user", "CREATE", "reservation", f"Temp Log {i}")
        
        # Verificar contadores independentes
        kelly_logs = self.audit_service.get_hotel_logs(hotel_kelly, self.user_kelly)
        temp_logs = self.audit_service.get_hotel_logs(hotel_temp, self.user_temp)
        
        assert len(kelly_logs) == 5
        assert len(temp_logs) == 5
        
        # Verificar que não há cruzamento
        kelly_hotel_ids = {log.hotel_id for log in kelly_logs}
        temp_hotel_ids = {log.hotel_id for log in temp_logs}
        
        assert kelly_hotel_ids == {hotel_kelly}
        assert temp_hotel_ids == {hotel_temp}
        assert kelly_hotel_ids.isdisjoint(temp_hotel_ids)
    
    def test_log_with_different_statuses(self):
        """Testa logging com diferentes status."""
        hotel_id = "test-hotel-123"
        
        # Criar logs com diferentes status
        success_log = self.audit_service.log_action(hotel_id, "user-1", "user@test.com", "user", "CREATE", "reservation", "Success", status="SUCCESS")
        failed_log = self.audit_service.log_action(hotel_id, "user-1", "user@test.com", "user", "CREATE", "reservation", "Failed", status="FAILED")
        error_log = self.audit_service.log_action(hotel_id, "user-1", "user@test.com", "user", "CREATE", "reservation", "Error", status="ERROR")
        
        # Verificar status
        assert success_log.status == "SUCCESS"
        assert failed_log.status == "FAILED"
        assert error_log.status == "ERROR"
        
        # Verificar estatísticas
        stats = self.audit_service.get_hotel_statistics(hotel_id, self.user_kelly)
        
        assert stats["total_actions"] == 3
        assert stats["successful_actions"] == 1
        assert stats["failed_actions"] == 2
        assert stats["success_rate"] == 33.33  # 1/3 * 100
    
    def test_permission_validation_edge_cases(self):
        """Testa casos extremos de validação de permissão."""
        hotel_id = "test-hotel-123"
        
        # Usuário sem hotel tentando acessar logs
        user_no_hotel = MockUser("user-no-hotel", "nohotel@test.com", None, "user")
        
        with pytest.raises(PermissionError):
            self.audit_service.get_hotel_logs(hotel_id, user_no_hotel)
        
        # Usuário com hotel diferente tentando acessar logs
        user_different_hotel = MockUser("user-diff", "diff@test.com", "other-hotel", "user")
        
        with pytest.raises(PermissionError):
            self.audit_service.get_hotel_logs(hotel_id, user_different_hotel)
        
        # Admin sem hotel (super admin) deve conseguir acessar
        admin_no_hotel = MockUser("admin-no-hotel", "admin@test.com", None, "admin")
        
        # Não deve levantar exceção
        result = self.audit_service.get_hotel_logs(hotel_id, admin_no_hotel)
        assert isinstance(result, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
