#!/usr/bin/env python
"""
Script para criar o banco de dados 'hotel' no PostgreSQL.

Uso:
    python create_database.py

Este script se conecta ao PostgreSQL usando as credenciais do .env
e cria o banco 'hotel' se ele não existir.
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv()

def create_database():
    """Cria o banco de dados 'hotel' se não existir."""
    
    # Extrai info da DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL não encontrado no .env")
        sys.exit(1)
    
    print("=" * 60)
    print("🗄️  CRIAÇÃO DO BANCO DE DADOS")
    print("=" * 60)
    print()
    
    # Parse da URL: postgresql://user:password@host:port/dbname
    try:
        # Remove o prefixo postgresql://
        url_parts = database_url.replace("postgresql://", "").split("@")
        user_pass = url_parts[0].split(":")
        host_port_db = url_parts[1].split("/")
        host_port = host_port_db[0].split(":")
        
        user = user_pass[0]
        password = user_pass[1]
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else "5432"
        dbname = host_port_db[1]
        
        print(f"📊 Host: {host}:{port}")
        print(f"👤 Usuário: {user}")
        print(f"🗄️  Banco: {dbname}")
        print()
        
    except Exception as e:
        print(f"❌ Erro ao parsear DATABASE_URL: {e}")
        print()
        print("💡 Formato esperado:")
        print("   postgresql://user:password@host:port/dbname")
        sys.exit(1)
    
    try:
        # Conecta ao postgres (banco padrão)
        print("🔌 Conectando ao PostgreSQL...")
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'  # Conecta ao banco padrão primeiro
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Verifica se banco existe
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (dbname,)
        )
        exists = cursor.fetchone()
        
        if exists:
            print(f"✅ Banco '{dbname}' já existe!")
        else:
            print(f"📦 Criando banco '{dbname}'...")
            cursor.execute(f'CREATE DATABASE {dbname}')
            print(f"✅ Banco '{dbname}' criado com sucesso!")
        
        cursor.close()
        conn.close()
        
        print()
        print("=" * 60)
        print("🎉 PRONTO!")
        print("=" * 60)
        print()
        print("🎯 Próximo passo:")
        print("   python -m app.tables")
        print()
        
    except psycopg2.OperationalError as e:
        print()
        print("=" * 60)
        print("❌ ERRO DE CONEXÃO")
        print("=" * 60)
        print()
        print(f"Detalhes: {e}")
        print()
        print("🔧 Verifique:")
        print("  1. PostgreSQL está rodando?")
        print("     Windows: services.msc → PostgreSQL")
        print("  2. Credenciais corretas no .env?")
        print("  3. Porta 5432 está aberta?")
        print()
        sys.exit(1)
    
    except Exception as e:
        print()
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    create_database()
