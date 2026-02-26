#!/usr/bin/env python
"""
🚀 Script para iniciar ngrok automaticamente

Uso:
    python start_ngrok.py

Isso vai:
1. Criar túnel ngrok para http://localhost:8000
2. Mostrar a URL pública
3. Dar instruções para configurar Twilio

"""

import sys
from pyngrok import ngrok

print("=" * 70)
print("🌐 INICIANDO NGROK TUNNEL")
print("=" * 70)
print()

try:
    # Inicia túnel para porta 8000
    print("📡 Criando túnel para http://localhost:8000...")
    tunnel = ngrok.connect(8000)
    public_url = tunnel.public_url
    
    print()
    print("=" * 70)
    print("✅ NGROK ATIVO!")
    print("=" * 70)
    print()
    print(f"🌐 URL Pública: {public_url}")
    print()
    print("=" * 70)
    print("🎯 CONFIGURE NO TWILIO AGORA:")
    print("=" * 70)
    print()
    print("1. Acesse: https://www.twilio.com/console/sms/whatsapp/sandbox")
    print()
    print("2. Em 'When a message comes in', cole:")
    print(f"   {public_url}/webhook/whatsapp/twilio")
    print()
    print("3. Clique em 'Save'")
    print()
    print("=" * 70)
    print("📱 TESTE NO WHATSAPP:")
    print("=" * 70)
    print()
    print("1. Envie mensagem para: +1 415 523 8886")
    print("2. Digite: 'Oi'")
    print("3. Aguarde resposta do bot!")
    print()
    print("=" * 70)
    print("⚠️  Mantenha este terminal aberto enquanto testa!")
    print("   Pressione Ctrl+C para encerrar.")
    print("=" * 70)
    print()
    
    # Mantém rodando
    print("🔄 Aguardando requisições...")
    print()
    
    # Bloqueia até Ctrl+C
    import time
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print()
    print()
    print("🛑 Encerrando ngrok...")
    ngrok.disconnect(public_url)
    print("✅ Túnel fechado!")
    print()

except Exception as e:
    print()
    print("=" * 70)
    print("❌ ERRO")
    print("=" * 70)
    print()
    print(f"Detalhes: {str(e)}")
    print()
    print("💡 Dica: Certifique-se de que:")
    print("  1. O FastAPI está rodando na porta 8000")
    print("  2. pyngrok está instalado: pip install pyngrok")
    print()
    sys.exit(1)
