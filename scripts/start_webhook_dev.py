#!/usr/bin/env python
"""
🚀 Helper Script - Inicia FastAPI + mostra instruções para ngrok

Uso:
    python start_webhook_dev.py

Isso vai:
1. Inicia FastAPI em http://localhost:8000
2. Mostra as instruções para ativar ngrok
3. Aguarda que você configure o webhook no Twilio
"""

import subprocess
import os
import platform
import sys


def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║   🚀 SETUP WEBHOOK - TWILIO WHATSAPP BIDIRECTIONAL            ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    print("📋 CHECKLIST ANTES DE COMEÇAR:")
    print("  ☑ Sandbox Twilio ativado? (join codigo no WhatsApp)")
    print("  ☑ Credenciais no .env? (TWILIO_ACCOUNT_SID, etc)")
    print("  ☑ ngrok instalado? (https://ngrok.com/download)")
    print()
    
    # Passo 1: Inicia FastAPI
    print("=" * 60)
    print("✅ PASSO 1: Iniciando FastAPI...")
    print("=" * 60)
    print()
    print("🎯 FastAPI vai rodar em:")
    print("   http://localhost:8000")
    print("   http://127.0.0.1:8000")
    print()
    
    cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
    
    try:
        # Inicia em sub-processo pra not bloquear
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # Deixa alguns segundos pra FastAPI iniciar
        import time
        time.sleep(3)
        
        print("✅ FastAPI iniciado!")
        print()
        
        # Passo 2: ngrok setup
        print("=" * 60)
        print("✅ PASSO 2: Ativar ngrok (EM OUTRO TERMINAL)")
        print("=" * 60)
        print()
        
        system = platform.system()
        
        if system == "Windows":
            print("🪟 Windows:")
            print()
            print("1. Abra novo PowerShell/CMD")
            print()
            print("2. Rode:")
            print("   cd C:\\ngrok")
            print("   .\\ngrok.exe http 8000")
            print()
        elif system == "Darwin":
            print("🍎 macOS:")
            print()
            print("1. Abra novo Terminal")
            print()
            print("2. Rode:")
            print("   ngrok http 8000")
            print()
        else:  # Linux
            print("🐧 Linux:")
            print()
            print("1. Abra novo Terminal")
            print()
            print("2. Rode:")
            print("   ngrok http 8000")
            print()
        
        # Passo 3: Configure URL no Twilio
        print("=" * 60)
        print("✅ PASSO 3: Configure Webhook no Twilio")
        print("=" * 60)
        print()
        print("1. Acesse: https://www.twilio.com/console/sms/whatsapp/sandbox")
        print()
        print("2. Procure: 'When a message comes in'")
        print()
        print("3. Copie a URL do ngrok (aparece lá)")
        print("   Exemplo: https://abc123xyz.ngrok.io")
        print()
        print("4. Adicione '/webhook/whatsapp/twilio'")
        print("   URL Final: https://abc123xyz.ngrok.io/webhook/whatsapp/twilio")
        print()
        print("5. Cole em Twilio Console e clique 'Save'")
        print()
        
        # Passo 4: Teste
        print("=" * 60)
        print("✅ PASSO 4: Teste!")
        print("=" * 60)
        print()
        print("1. Abra WhatsApp no seu celular")
        print()
        print("2. Envie para: +1 415 523 8886")
        print("   Mensagem: 'Oi'")
        print()
        print("3. Você vai receber a resposta do bot!")
        print()
        print("4. Verifique os logs aqui embaixo 👇")
        print()
        print("=" * 60)
        print("📊 LOGS - FastAPI")
        print("=" * 60)
        print()
        
        # Mostra output do FastAPI em tempo real
        for line in process.stdout:
            print(line, end='')
        
    except KeyboardInterrupt:
        print()
        print()
        print("🛑 FastAPI desligado (Ctrl+C)")
        print()
        print("💡 Dica: Deixe ngrok rodando pra continuar testando!")
        print()
    except Exception as e:
        print(f"❌ Erro ao iniciar FastAPI: {str(e)}")
        print()
        print("Tente rodar manualmente:")
        print("  python -m uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
