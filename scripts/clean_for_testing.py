#!/usr/bin/env python
"""
Script para limpar reservas do banco e conversas do Redis.

Use para resetar o ambiente antes de testes reais (WhatsApp, fluxo completo).

Uso:
    python scripts/clean_for_testing.py

Ou via Makefile:
    make clean-for-testing
"""
import os
import sys

# Garante que o app está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.infrastructure.persistence.sql.database import engine, init_db
from app.infrastructure.cache.redis_repository import RedisRepository


def clean_reservations_and_related(session) -> int:
    """Remove reservas e tabelas relacionadas (ordem respeitando FKs)."""
    # Ordem: tabelas que referenciam reservations primeiro
    tables = [
        "payments",
        "support_tickets",
        "room_orders",
        "proactive_message_log",
        "reservations",
    ]
    total = 0
    for table in tables:
        result = session.execute(text(f"DELETE FROM {table}"))
        total += result.rowcount
    return total


def clean_conversation_data(session) -> int:
    """Remove dados de conversas/leads do banco SQL."""
    tables = [
        "conversation_cache",
        "saas_analytics_events",
        "saas_leads",
    ]
    total = 0
    for table in tables:
        try:
            result = session.execute(text(f"DELETE FROM {table}"))
            total += result.rowcount
        except Exception:
            # Tabela pode não existir em todas as migrações
            pass
    return total


def main() -> None:
    from app.infrastructure.persistence.sql.database import SessionLocal

    init_db()

    print("=" * 50)
    print("🧹 Limpeza para testes reais")
    print("=" * 50)

    # 1. Banco de dados
    session = SessionLocal()
    try:
        deleted_reservations = clean_reservations_and_related(session)
        deleted_conversations = clean_conversation_data(session)
        session.commit()
        print(f"✅ Banco: {deleted_reservations} registros de reservas/pagamentos removidos")
        print(f"✅ Banco: {deleted_conversations} registros de conversas/leads removidos")
    except Exception as e:
        session.rollback()
        print(f"❌ Erro ao limpar banco: {e}")
        sys.exit(1)
    finally:
        session.close()

    # 2. Redis
    try:
        cache = RedisRepository()
        cache.clear()
        print("✅ Redis: cache de conversas limpo (FLUSHDB)")
    except Exception as e:
        print(f"❌ Erro ao limpar Redis: {e}")
        sys.exit(1)

    print("=" * 50)
    print("✅ Ambiente pronto para testes reais.")
    print("=" * 50)


if __name__ == "__main__":
    main()
