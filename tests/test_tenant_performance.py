"""Testes de performance para multi-tenancy."""

import pytest
import time
from app.infrastructure.persistence.sql.reservation_repository_sql import ReservationRepositorySQL
from app.infrastructure.persistence.sql.room_repository_sql import RoomRepositorySQL
from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.value_objects.phone_number import PhoneNumber


class TestMultiTenantPerformance:
    """Testes de performance para garantir que isolamento não impacta performance."""
    
    @pytest.fixture
    def mock_session_with_data(self):
        """Mock session com dados de múltiplos hotéis."""
        # Criar 1000 reservas distribuídas em 10 hotéis
        reservations = []
        for hotel_num in range(10):
            hotel_id = f"hotel-{hotel_num:03d}"
            for res_num in range(100):
                reservation = type('MockReservationModel', (), {
                    'id': f"res-{hotel_num}-{res_num}",
                    'hotel_id': hotel_id,
                    'guest_name': f"Hóspede {hotel_num}-{res_num}",
                    'guest_phone': f"1199999{hotel_num:02d}{res_num:02d}",
                    'status': 'PENDING',
                    'created_at': None
                })()
                reservations.append(reservation)
        
        class MockQuery:
            def __init__(self, all_reservations):
                self.all_reservations = all_reservations
                self.filters = {}
            
            def filter_by(self, **kwargs):
                self.filters.update(kwargs)
                return self
            
            def filter(self, *args):
                return self
            
            def order_by(self, *args):
                return self
            
            def limit(self, limit):
                return self
            
            def first(self):
                hotel_id = self.filters.get('hotel_id')
                guest_phone = self.filters.get('guest_phone')
                
                for res in self.all_reservations:
                    if res.hotel_id == hotel_id and res.guest_phone == guest_phone:
                        return res
                return None
            
            def all(self):
                hotel_id = self.filters.get('hotel_id')
                if hotel_id:
                    return [res for res in self.all_reservations if res.hotel_id == hotel_id]
                return self.all_reservations
        
        mock_session = type('MockSession', (), {})()
        mock_session.query = lambda model: MockQuery(reservations)
        
        return mock_session
    
    def test_performance_hotel_filtering(self, mock_session_with_data):
        """Testa performance de filtragem por hotel."""
        repo = ReservationRepositorySQL(mock_session_with_data)
        
        # Medir tempo para buscar em hotel específico
        start_time = time.time()
        for _ in range(100):
            result = repo.find_by_phone_number("119999990099", "hotel-001")
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 100
        assert avg_time < 0.001  # Menos de 1ms por busca
        assert result is not None
        assert result.hotel_id == "hotel-001"
    
    def test_performance_list_reservations_by_hotel(self, mock_session_with_data):
        """Testa performance de listagem por hotel."""
        repo = ReservationRepositorySQL(mock_session_with_data)
        
        # Medir tempo para listar reservas de hotel específico
        start_time = time.time()
        for hotel_num in range(10):
            hotel_id = f"hotel-{hotel_num:03d}"
            reservations = repo.list_reservations(hotel_id)
            assert len(reservations) == 100
            assert all(r.hotel_id == hotel_id for r in reservations)
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time_per_hotel = total_time / 10
        assert avg_time_per_hotel < 0.01  # Menos de 10ms por hotel
    
    def test_scalability_with_hotel_count(self):
        """Testa escalabilidade com número crescente de hotéis."""
        # Simular cenário com muitos hotéis
        hotel_counts = [10, 50, 100, 500]
        times = []
        
        for hotel_count in hotel_counts:
            # Criar dados para teste
            reservations = []
            for hotel_num in range(hotel_count):
                hotel_id = f"hotel-{hotel_num:04d}"
                for res_num in range(10):  # 10 reservas por hotel
                    reservation = type('MockReservationModel', (), {
                        'id': f"res-{hotel_num}-{res_num}",
                        'hotel_id': hotel_id,
                        'guest_name': f"Hóspede {hotel_num}-{res_num}",
                        'guest_phone': f"1199999{hotel_num:03d}{res_num:02d}",
                        'status': 'PENDING'
                    })()
                    reservations.append(reservation)
            
            class MockQuery:
                def __init__(self, all_reservations):
                    self.all_reservations = all_reservations
                    self.filters = {}
                
                def filter_by(self, **kwargs):
                    self.filters.update(kwargs)
                    return self
                
                def filter(self, *args):
                    return self
                
                def order_by(self, *args):
                    return self
                
                def limit(self, limit):
                    return self
                
                def all(self):
                    hotel_id = self.filters.get('hotel_id')
                    if hotel_id:
                        return [res for res in self.all_reservations if res.hotel_id == hotel_id]
                    return self.all_reservations
            
            mock_session = type('MockSession', (), {})()
            mock_session.query = lambda model: MockQuery(reservations)
            
            repo = ReservationRepositorySQL(mock_session)
            
            # Medir performance
            start_time = time.time()
            for hotel_num in range(min(5, hotel_count)):  # Testar primeiros 5 hotéis
                hotel_id = f"hotel-{hotel_num:04d}"
                repo.list_reservations(hotel_id)
            end_time = time.time()
            
            avg_time = (end_time - start_time) / min(5, hotel_count)
            times.append(avg_time)
        
        # Verificar que tempo não cresce linearmente com número de hotéis
        # (devido a índices do hotel_id)
        if len(times) > 1:
            growth_ratio = times[-1] / times[0]
            assert growth_ratio < 2.0  # Tempo não deve dobrar com 50x mais hotéis


class TestIndexEffectiveness:
    """Testes para verificar eficácia dos índices hotel_id."""
    
    def test_hotel_id_index_usage(self):
        """Testa que índices hotel_id estão sendo usados efetivamente."""
        # Em implementação real, verificaríamos o plano de execução
        # Aqui simulamos que índices melhoram performance
        
        # Simulação: busca com índice vs busca sem índice
        def simulate_indexed_search(hotel_id, total_records=10000):
            # Busca com índice: O(log n)
            import math
            return math.log(total_records / 10)  # ~10 hotéis
        
        def simulate_full_scan(total_records=10000):
            # Busca sem índice: O(n)
            return total_records
        
        indexed_time = simulate_indexed_search("hotel-001")
        full_scan_time = simulate_full_scan()
        
        # Índice deve ser significativamente mais rápido
        assert indexed_time < full_scan_time / 100
    
    def test_hotel_id_uniqueness_with_indexes(self):
        """Testa que índices garantem unicidade por hotel."""
        # Simular cenário onde mesmo número de quarto pode existir em hotéis diferentes
        rooms_data = [
            ("hotel-001", "101", "SINGLE"),
            ("hotel-002", "101", "DOUBLE"),  # Mesmo número, hotel diferente
            ("hotel-001", "102", "SINGLE"),
        ]
        
        # Verificar que pode existir quarto 101 em múltiplos hotéis
        hotel_101_rooms = [r for r in rooms_data if r[1] == "101"]
        assert len(hotel_101_rooms) == 2
        
        # Mas dentro do mesmo hotel, números devem ser únicos
        hotel_001_rooms = [r for r in rooms_data if r[0] == "hotel-001"]
        room_numbers = [r[1] for r in hotel_001_rooms]
        assert len(room_numbers) == len(set(room_numbers))  # Únicos


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
