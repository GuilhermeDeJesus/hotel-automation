#!/usr/bin/env python3.14
"""
Teste real de chat com OpenAI - verifica se tem saldo.
"""
import sys
import os

if 'msys64' in sys.executable.lower():
    print("❌ Use: py test_real_chat.py")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import openai

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    
    print("=" * 70)
    print("💬 Teste de Chat Real com OpenAI")
    print("=" * 70 + "\n")
    
    client = openai.OpenAI(api_key=api_key)
    
    try:
        print("⏳ Enviando mensagem para OpenAI...")
        print("  Modelo: gpt-3.5-turbo")
        print("  Mensagem: 'Olá, você consegue me responder?'\n")
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Olá, você consegue me responder?"}
            ],
            max_tokens=50,
        )
        
        print("✅ SUCESSO! Requisição completada!\n")
        print("📊 Resposta recebida:")
        print(f"   {response.choices[0].message.content}\n")
        
        print("📈 Uso de tokens:")
        print(f"   - Input: {response.usage.prompt_tokens}")
        print(f"   - Output: {response.usage.completion_tokens}")
        print(f"   - Total: {response.usage.total_tokens}\n")
        
        print("=" * 70)
        print("✅ Tudo funcionando! Você TEM saldo na chave OpenAI!")
        print("=" * 70)
        
    except openai.RateLimitError as e:
        print(f"❌ ERRO 429: Sem saldo ou limite excedido")
        print(f"Mensagem: {str(e)}\n")
        print("Ações:")
        print("1. Ir em https://platform.openai.com/account/billing/overview")
        print("2. Clicar em 'Add to credit balance'")
        print("3. Adicionar $5-$20 de crédito\n")
        
    except Exception as e:
        print(f"❌ Erro: {type(e).__name__}")
        print(f"Detalhes: {str(e)}\n")

if __name__ == "__main__":
    main()
