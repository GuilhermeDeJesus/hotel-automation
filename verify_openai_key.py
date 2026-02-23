#!/usr/bin/env python3.14
"""
Diagnóstico da chave OpenAI - verifica se é válida e se tem saldo.
"""
import sys
import os

if 'msys64' in sys.executable.lower():
    print("❌ Use: py verify_openai_key.py")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import openai

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    
    print("=" * 70)
    print("🔍 OpenAI API Key Diagnostic")
    print("=" * 70 + "\n")
    
    if not api_key:
        print("❌ OPENAI_API_KEY não configurada no .env\n")
        sys.exit(1)
    
    # Mostrar parte da chave
    masked_key = api_key[:20] + "..." + api_key[-10:]
    print(f"Chave carregada: {masked_key}")
    print(f"Tamanho: {len(api_key)} caracteres")
    print(f"Formato: {'✓ sk-proj' if api_key.startswith('sk-proj') else '⚠️ Outro formato'}\n")
    
    # Tentar listar modelos (requisição leve para verificar)
    print("-" * 70)
    print("🔄 Testando acesso à API...")
    print("-" * 70)
    
    try:
        client = openai.OpenAI(api_key=api_key)
        
        # Tentar listar modelos (muito leve, só validação)
        print("⏳ Fazendo requisição para listar modelos...")
        models = client.models.list()
        
        print(f"✅ Conexão bem-sucedida!")
        print(f"✅ Chave é válida e tem acesso à API")
        print(f"📊 Modelos disponíveis: {len(models.data)}\n")
        
        # Mostrar alguns modelos GPT
        gpt_models = [m.id for m in models.data if 'gpt' in m.id]
        if gpt_models:
            print("Modelos GPT disponíveis:")
            for model in sorted(gpt_models)[:5]:
                print(f"  ✓ {model}")
            if len(gpt_models) > 5:
                print(f"  ... e mais {len(gpt_models) - 5}")
        
    except openai.AuthenticationError as e:
        print(f"❌ ERRO: Chave inválida ou expirada")
        print(f"   Mensagem: {str(e)}\n")
        print("💡 Soluções:")
        print("  1. Regenera a chave em https://platform.openai.com/api-keys")
        print("  2. Verifica se a chave está sendo copiada corretamente")
        print("  3. Confirma que não há espaços extras no .env\n")
        
    except openai.RateLimitError as e:
        print(f"⚠️  ERRO 429: Sem saldo ou limite excedido")
        print(f"   Mensagem: {str(e)}\n")
        print("💡 Soluções:")
        print("  1. Adicionar crédito em https://platform.openai.com/account/billing/overview")
        print("  2. Verificar se trial expirou (https://platform.openai.com/account/billing/overview)")
        print("  3. Confirmar que payment method está ativo\n")
        
    except Exception as e:
        print(f"❌ ERRO: {type(e).__name__}")
        print(f"   Mensagem: {str(e)}\n")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
