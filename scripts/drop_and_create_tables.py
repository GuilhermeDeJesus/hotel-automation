#!/usr/bin/env python
"""
Script para DROPAR e RECRIAR todas as tabelas.

⚠️  ATENÇÃO: Este script vai DELETAR todos os dados!

Uso:
    python drop_and_create_tables.py
"""

import sys
from sqlalchemy.exc import OperationalError

try:
    from app.infrastructure.persistence.sql.database import Base, engine, DATABASE_URL
    from app.infrastructure.persistence.sql.models import (
        CustomerModel, 
        ReservationModel, 
        PaymentModel,
        ConversationCacheModel
    )
    
    print("=" * 60)
    print("⚠️  DROPAR E RECRIAR TABELAS - HOTEL AUTOMATION")
    print("=" * 60)
    print()
    print(f"📊 Database: {DATABASE_URL}")
    print()
    print("⚠️  ATENÇÃO: Todos os dados serão PERDIDOS!")
    print()
    
    # Confirma ação
    confirm = input("Digite 'SIM' para continuar: ")
    
    if confirm.upper() != "SIM":
        print()
        print("❌ Operação cancelada.")
        sys.exit(0)
    
    print()
    print("🗑️  Dropando tabelas existentes...")
    
    # Drop todas as tabelas
    Base.metadata.drop_all(bind=engine)
    
    print("✅ Tabelas dropadas!")
    print()
    print("📦 Criando novas tabelas:")
    print("  ✓ customers")
    print("  ✓ reservations")
    print("  ✓ payments")
    print("  ✓ conversation_cache")
    print()
    
    # Cria todas as tabelas
    Base.metadata.create_all(bind=engine)
    
    print("=" * 60)
    print("✅ SUCESSO! Tabelas recriadas com nova estrutura.")
    print("=" * 60)
    print()
    print("🎯 Próximos passos:")
    print("  1. Inicie o servidor: python -m uvicorn app.main:app --reload")
    print("  2. Configure webhook com ngrok")
    print("  3. Teste no WhatsApp!")
    print()

except OperationalError as e:
    print("=" * 60)
    print("❌ ERRO DE CONEXÃO COM O BANCO")
    print("=" * 60)
    print()
    print(f"Detalhes: {str(e)}")
    print()
    print("🔧 Verifique:")
    print("  1. PostgreSQL está rodando?")
    print("  2. DATABASE_URL está correto no .env?")
    print("  3. Banco de dados 'hotel' existe?")
    print()
    sys.exit(1)

except Exception as e:
    print("=" * 60)
    print("❌ ERRO")
    print("=" * 60)
    print()
    print(f"Detalhes: {str(e)}")
    print()
    import traceback
    traceback.print_exc()
    sys.exit(1)
