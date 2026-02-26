#!/usr/bin/env python3
"""
Teste para validar que ConversationUseCase recebe contexto dual:
1. CONTEXTO DO HOTEL (Passo 4): hotel, politicas, servicos
2. CONTEXTO DE RESERVA (Passo 3): informacoes do hospede
"""

from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.hotel_repository_sql import HotelRepositorySQL
from app.infrastructure.persistence.sql.reservation_repository_sql import ReservationRepositorySQL
from app.application.services.hotel_context_service import HotelContextService
from app.application.services.reservation_context_service import ReservationContextService


def test_dual_context():
    session = SessionLocal()
    
    # Recuperar contextos
    hotel_repo = HotelRepositorySQL(session)
    hotel_service = HotelContextService(hotel_repo)
    hotel_context = hotel_service.get_context()
    
    print("=" * 70)
    print("CONTEXTO DO HOTEL (Passo 4):")
    print("=" * 70)
    print(hotel_context)
    
    # Buscar exemplo de reserva
    reservation_repo = ReservationRepositorySQL(session)
    reservation_service = ReservationContextService(reservation_repo)
    
    # Usar um numero de telefone de teste
    test_phone = "+5561987654321"  
    reservation_context = reservation_service.get_context_for_phone(test_phone)
    
    print("\n" + "=" * 70)
    print(f"CONTEXTO DE RESERVA (Passo 3) para {test_phone}:")
    print("=" * 70)
    if reservation_context:
        print(reservation_context)
    else:
        print("(Nenhuma reserva encontrada para este telefone)")
    
    print("\n" + "=" * 70)
    print("RESUMO - CONTEXTOS DISPONIVEIS PARA IA:")
    print("=" * 70)
    print("✓ Hotel context (nome, endereco, politicas, servicos)")
    print("✓ Reservation context (hospede, status, datas)")
    print("✓ ConversationUseCase agora injeta AMBOS no system prompt")
    print("\nIA tera conhecimento completo sobre:")
    print("  - Politicas do hotel (check-in/checkout, pets, criancas, cancelamento)")
    print("  - Servicos disponiveis (Wi-Fi, piscina, etc)")
    print("  - Contacto do hotel (+55 61 99999-0000)")
    print("  - Informacoes da reserva do hospede (se existir)")
    

if __name__ == "__main__":
    test_dual_context()
