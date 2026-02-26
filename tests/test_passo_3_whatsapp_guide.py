"""
GUIA PRÁTICO - Testando Passo 3 com WhatsApp Real

Este script configura e orienta como testar a integração de contexto de reserva
com mensagens reais via WhatsApp/Twilio.
"""
import subprocess
import time
import os
from datetime import date
import uuid

from app.infrastructure.persistence.sql.database import SessionLocal, init_db
from app.infrastructure.persistence.sql.models import ReservationModel


def create_test_reservation():
    """Criar reserva de teste com número de telefone real do Sandbox Twilio."""
    print("\n" + "="*70)
    print("📝 CRIANDO RESERVA DE TESTE PARA O SANDBOX")
    print("="*70 + "\n")
    
    session = SessionLocal()
    init_db()
    
    # Use o número de teste do próprio Twilio Sandbox
    # Formato: +1 415 523 8886 (sandbox padrão) ou seu número de teste
    phone = "+1 415 523 8886"  # Número padrão do Twilio Sandbox
    
    # Limpar reservas anteriores
    session.query(ReservationModel).filter_by(guest_phone=phone).delete()
    session.commit()
    
    # Criar nova reserva
    reservation = ReservationModel(
        id=str(uuid.uuid4()),
        guest_name="Teste Sandbox",
        guest_phone=phone,
        status="CONFIRMED",
        check_in_date=date(2026, 3, 1),
        check_out_date=date(2026, 3, 7),
        room_number="Suite 01",  # Max 10 chars
        total_amount=5000.00,
        notes="Cliente em teste - Passo 3 IA com contexto"
    )
    
    session.add(reservation)
    session.commit()
    
    print(f"✅ Reserva criada com sucesso!")
    print(f"   📞 Telefone: {phone}")
    print(f"   👤 Hóspede: Teste Sandbox")
    print(f"   🏨 Quarto: Suite 01")
    print(f"   📅 Check-in: 01/03/2026")
    print(f"   📅 Check-out: 07/03/2026")
    print(f"   💰 Total: R$ 5.000,00")
    print(f"   📝 Notas: Cliente em teste - Passo 3 IA com contexto\n")
    
    session.close()


def show_ngrok_instructions():
    """Mostrar instruções de como iniciar ngrok."""
    print("\n" + "="*70)
    print("🌐 CONFIGURANDO NGROK (Tunnel Local → Internet)")
    print("="*70 + "\n")
    
    print("Execute em outro terminal PowerShell:\n")
    print("    python start_ngrok.py\n")
    print("Ou manualmente:\n")
    print("    ngrok http 8000\n")
    print("⚠️  COPIE A URL HTTPS gerada (exemplo: https://abc123.ngrok.io)\n")


def show_twilio_instructions():
    """Mostrar instruções de como configurar Twilio."""
    print("\n" + "="*70)
    print("📱 CONFIGURANDO WEBHOOK NO TWILIO SANDBOX")
    print("="*70 + "\n")
    
    print("1. Acesse: https://console.twilio.com/develop/sms/try-it-out/whatsapp-sandbox")
    print("\n2. Em 'When a message comes in', configure:\n")
    print("   URL: https://YOUR_NGROK_URL/webhook/whatsapp/twilio")
    print("   (Substitua YOUR_NGROK_URL pela URL do ngrok)\n")



def show_test_instructions(phone):
    """Mostrar instruções de teste."""
    print("\n" + "="*70)
    print("💬 ENVIANDO MENSAGEM DE TESTE")
    print("="*70 + "\n")
    
    print("Agora teste MENSAGENS DIFERENTES para ver o Passo 3 em ação:\n")
    
    messages = [
        ("Oi", "Resposta genérica com contexto: 'oi, você tem uma reserva confirmada...'"),
        ("Qual minha reserva?", "Contexto completo: quarto, datas, valor, notas"),
        ("Quando é meu check-in?", "IA responde usando data do contexto (01/03/2026)"),
        ("Preciso de algo especial", "IA vê as notas 'Suite Presidential' e conhece preferências"),
        ("check-in", "Processa como comando de check-in"),
    ]
    
    print("OPÇÕES DE TESTE:\n")
    for i, (msg, expected) in enumerate(messages, 1):
        print(f"{i}. Envie: \"{msg}\"")
        print(f"   Esperado: {expected}\n")
    
    print("="*70)


def show_logs_instructions():
    """Mostrar como ver os logs."""
    print("\n" + "="*70)
    print("📊 MONITORANDO LOGS")
    print("="*70 + "\n")
    
    print("A. No terminal do FastAPI (porta 8000):")
    print("   ✓ Veja INFO logs das requisições")
    print("   ✓ Veja DEBUG logs di processamento\n")
    
    print("B. No terminal do ngrok:")
    print("   ✓ Veja todas as requisições HTTP")
    print("   ✓ Status 200 = sucesso\n")
    
    print("C. No arquivo de log de conversas:")
    print("   📄 conversations.log\n")


def show_debugging_tips():
    """Mostrar dicas de debug."""
    print("\n" + "="*70)
    print("🔍 DICAS DE DEBUG")
    print("="*70 + "\n")
    
    print("❌ Se a mensagem NÃO chegar:")
    print("   1. Verifique se ngrok está ativo (execute 'python start_ngrok.py')")
    print("   2. Copie a URL HTTPS correta do ngrok")
    print("   3. Atualize o URL no Twilio Console")
    print("   4. Espere 30 segundos e tente novamente\n")
    
    print("❌ Se receber erro 404:")
    print("   1. O URL no Twilio pode estar errado")
    print("   2. Verifique se é exatamente '/webhook/whatsapp/twilio'")
    print("   3. Tente: https://YOUR_NGROK_URL/webhook/whatsapp/twilio\n")
    
    print("❌ Se a IA não responde com contexto:")
    print("   1. Verifique se a reserva foi criada com o número correto")
    print("   2. O telefone do Twilio Sandbox precisa ser +1 415 523 8886")
    print("   3. Rode 'python test_passo_3.py' para validar\n")
    
    print("✅ SE TUDO FUNCIONA:")
    print("   1. Você receberá a mensagem 'Oi' do bot")
    print("   2. A resposta terá contexto da reserva (Quarto, datas, etc)")
    print("   3. Qualquer pergunta sobre a reserva será respondida com dados reais\n")


def show_quick_start():
    """Resumo rápido do quick start."""
    print("\n" + "="*70)
    print("⚡ QUICK START (3 PASSOS)")
    print("="*70 + "\n")
    
    print("TERMINAL 1 - FastAPI Server:")
    print("   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000\n")
    
    print("TERMINAL 2 - NgRok Tunnel:")
    print("   python start_ngrok.py\n")
    
    print("ENTÃO:")
    print("   1. Copie URL HTTPS do ngrok")
    print("   2. Configure URL no Twilio Console")
    print("   3. Envie mensagem WhatsApp para +1 415 523 8886\n")
    
    print("RESULTADO:")
    print("   ✅ Bot responde com contexto real da reserva!\n")


def main():
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  🚀 TESTANDO PASSO 3 - CONTEXTO DE RESERVA NA IA".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    # Step 1: Create test reservation
    create_test_reservation()
    
    # Step 2: Show instructions
    show_quick_start()
    show_ngrok_instructions()
    show_twilio_instructions()
    show_test_instructions("+1 415 523 8886")
    show_logs_instructions()
    show_debugging_tips()
    
    print("\n" + "="*70)
    print("📌 PRÓXIMOS PASSOS")
    print("="*70 + "\n")
    
    print("1. Execute: python start_ngrok.py")
    print("2. Configure URL no Twilio")
    print("3. Envie mensagem WhatsApp")
    print("4. Veja resposta com contexto! 🎉\n")
    
    print("Documentação completa: https://github.com/seu-repo")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
