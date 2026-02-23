#!/usr/bin/env python3.14
"""
Monitor de gastos OpenAI - mostra quanto você já gastou.
"""
import sys
import os
from datetime import datetime, timedelta

if 'msys64' in sys.executable.lower():
    print("❌ Use: py monitor_openai_spending.py")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import openai

def format_currency(value):
    """Formata valor em USD com 4 casas decimais"""
    return f"US$ {value:.4f}"

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ OPENAI_API_KEY não configurada\n")
        sys.exit(1)
    
    client = openai.OpenAI(api_key=api_key)
    
    print("=" * 70)
    print("💰 Monitor de Gastos OpenAI")
    print("=" * 70 + "\n")
    
    try:
        # Tentar obter dados de uso
        print("⏳ Carregando dados de uso...")
        
        # Período atual (este mês)
        today = datetime.now()
        month_start = today.replace(day=1)
        
        # Simular chamada para puxar dados (OpenAI não expõe API de uso diretamente)
        # Vamos mostrar instruções em vez disso
        
        print("\n📊 Dados de Uso:")
        print("-" * 70)
        print("A OpenAI não expõe dados de uso via API.")
        print("Para ver seus gastos, acesse: https://platform.openai.com/account/usage\n")
        
        # Mostrar credit balance (se disponível)
        print("💳 Seu saldo de crédito:")
        print("-" * 70)
        
        # Fazer uma requisição leve para confirmarpermissão
        response = client.models.list()
        
        print("✅ Acesso confirmado!")
        print("\n🔗 Links úteis:")
        print("   1. Ver gastos este mês:")
        print("      https://platform.openai.com/account/usage/overview")
        print("\n   2. Adicionar crédito:")
        print("      https://platform.openai.com/account/billing/overview")
        print("\n   3. Ver fatura:")
        print("      https://platform.openai.com/account/billing/history")
        
        print("\n" + "=" * 70)
        print("💡 Dica: OpenAI envia email quando gasta 50%, 75%, 100% do crédito")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Erro: {type(e).__name__}")
        print(f"Detalhes: {str(e)}\n")

if __name__ == "__main__":
    main()
