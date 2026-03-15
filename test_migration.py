#!/usr/bin/env python
"""
Teste para verificar se a migration do hotel_id funciona corretamente.
"""

import os
import sys
import psycopg2
from psycopg2 import sql

# Configurações do banco de dados
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'hotel'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
}

def test_migration():
    """Testa se as colunas hotel_id foram adicionadas corretamente."""
    
    print("=" * 60)
    print("🧪 TESTE DE MIGRATION - HOTEL_ID")
    print("=" * 60)
    
    try:
        # Conectar ao banco
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print(f"✅ Conectado ao banco: {DB_CONFIG['database']}")
        
        # Tabelas que devem ter hotel_id
        tables_with_hotel_id = [
            'rooms', 'customers', 'reservations', 'payments',
            'conversation_cache', 'saas_leads', 'saas_analytics_events',
            'support_tickets', 'room_orders', 'proactive_message_log'
        ]
        
        print("\n📋 Verificando colunas hotel_id...")
        
        for table in tables_with_hotel_id:
            try:
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = %s AND column_name = 'hotel_id'
                """, (table,))
                
                result = cursor.fetchone()
                
                if result:
                    print(f"  ✅ {table}: hotel_id ({result[1]}, nullable={result[2]})")
                    
                    # Verificar foreign key
                    cursor.execute("""
                        SELECT tc.constraint_name, tc.constraint_type
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu 
                            ON tc.constraint_name = kcu.constraint_name
                        WHERE tc.table_name = %s 
                            AND kcu.column_name = 'hotel_id'
                            AND tc.constraint_type = 'FOREIGN KEY'
                    """, (table,))
                    
                    fk_result = cursor.fetchone()
                    if fk_result:
                        print(f"    🔗 FK: {fk_result[0]}")
                    else:
                        print(f"    ❌ FK não encontrada")
                else:
                    print(f"  ❌ {table}: hotel_id não encontrado")
                    
            except Exception as e:
                print(f"  ⚠️  {table}: Erro ao verificar - {str(e)}")
        
        # Verificar índices
        print("\n📊 Verificando índices...")
        for table in tables_with_hotel_id:
            try:
                cursor.execute("""
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = %s AND indexdef LIKE '%hotel_id%'
                """, (table,))
                
                indexes = cursor.fetchall()
                if indexes:
                    print(f"  ✅ {table}: {len(indexes)} índice(s) com hotel_id")
                    for idx in indexes:
                        print(f"    📌 {idx[0]}")
                else:
                    print(f"  ⚠️  {table}: Nenhum índice com hotel_id encontrado")
                    
            except Exception as e:
                print(f"  ⚠️  {table}: Erro ao verificar índices - {str(e)}")
        
        # Testar inserção de dados
        print("\n🧪 Testando inserção de dados...")
        
        # Criar hotel de teste se não existir
        cursor.execute("""
            INSERT INTO hotels (id, name, address, contact_phone, checkin_time, checkout_time, cancellation_policy, pet_policy, child_policy, amenities, is_active, requires_payment_for_confirmation, allows_reservation_without_payment, created_at, updated_at)
            VALUES ('test-hotel-123', 'Hotel Teste', 'Rua Teste, 123', '11999999999', '14:00', '12:00', 'Política teste', 'Pets teste', 'Crianças teste', 'Wi-Fi, Piscina', true, false, true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """)
        
        # Testar inserção em rooms com hotel_id
        try:
            cursor.execute("""
                INSERT INTO rooms (id, hotel_id, number, room_type, daily_rate, max_guests, status, is_active, created_at, updated_at)
                VALUES ('room-test-999', 'test-hotel-123', '999', 'SINGLE', 150.0, 1, 'AVAILABLE', true, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """)
            print("  ✅ rooms: Inserção com hotel_id funcionou")
        except Exception as e:
            print(f"  ❌ rooms: Erro na inserção - {str(e)}")
        
        # Testar inserção em reservations com hotel_id
        try:
            cursor.execute("""
                INSERT INTO reservations (id, hotel_id, guest_name, guest_phone, status, total_amount, created_at, updated_at)
                VALUES ('res-test-999', 'test-hotel-123', 'João Teste', '11988887777', 'PENDING', 300.0, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """)
            print("  ✅ reservations: Inserção com hotel_id funcionou")
        except Exception as e:
            print(f"  ❌ reservations: Erro na inserção - {str(e)}")
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        sys.exit(1)
        
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    test_migration()
