"""
Test Script: Testar integração com Twilio WhatsApp API

Uso:
    python test_whatsapp_twilio.py

Requisitos:
    - Variáveis de ambiente configuradas (.env)
    - Conta Twilio criada
    - Sandbox WhatsApp ativado OU número próprio adicionado
"""

import os
import sys
import logging
from dotenv import load_dotenv
from app.infrastructure.messaging.whatsapp_twilio_client import WhatsAppTwilioClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


def test_connection():
    """Testa conexão básica com Twilio API."""
    print("\n" + "="*60)
    print("TEST 1: Testar Conexão com Twilio API")
    print("="*60)
    
    try:
        client = WhatsAppTwilioClient()
        logger.info("✅ Cliente Twilio WhatsApp inicializado")
        
        # Testa conexão
        if client.test_connection():
            logger.info("✅ Conexão com Twilio API OK!")
            return client
        else:
            logger.error("❌ Erro na conexão com Twilio API")
            return None
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar: {str(e)}")
        return None


def test_send_message(client: WhatsAppTwilioClient):
    """Testa envio de mensagem de texto."""
    print("\n" + "="*60)
    print("TEST 2: Enviar Mensagem de Texto")
    print("="*60)
    
    # Seu número de teste
    to_phone = "+5561998776092"  # Troque pelo seu número!
    message = "Olá! Esta é uma mensagem de teste do Twilio WhatsApp API 🚀"
    
    logger.info(f"Enviando para: {to_phone}")
    logger.info(f"Mensagem: {message}")
    
    result = client.send_text_message(to_phone, message)
    
    if result["success"]:
        logger.info(f"✅ Mensagem enviada! SID: {result['sid']}")
        logger.info(f"📊 Status: {result['status']}")
        logger.info("📱 Verifique seu WhatsApp em alguns segundos...")
        return True
    else:
        logger.error(f"❌ Erro ao enviar: {result['error']}")
        if "code" in result:
            logger.error(f"❌ Código de erro: {result['code']}")
        return False


def test_send_media(client: WhatsAppTwilioClient):
    """Testa envio de mensagem com mídia."""
    print("\n" + "="*60)
    print("TEST 3: Enviar Mensagem com Mídia")
    print("="*60)
    
    to_phone = "+5561998776092"
    message = "Aqui está uma imagem de exemplo!"
    media_url = "https://demo.twilio.com/owl.png"  # Imagem de teste da Twilio
    
    logger.info(f"Enviando mídia para: {to_phone}")
    logger.info(f"URL: {media_url}")
    
    result = client.send_media_message(to_phone, message, media_url)
    
    if result["success"]:
        logger.info(f"✅ Mensagem com mídia enviada! SID: {result['sid']}")
        logger.info("🖼️  Verifique a imagem no WhatsApp...")
        return True
    else:
        logger.error(f"❌ Erro ao enviar: {result['error']}")
        return False


def test_message_status(client: WhatsAppTwilioClient, message_sid: str):
    """Testa consulta de status de mensagem."""
    print("\n" + "="*60)
    print("TEST 4: Consultar Status de Mensagem")
    print("="*60)
    
    logger.info(f"Consultando status da mensagem: {message_sid}")
    
    result = client.get_message_status(message_sid)
    
    if result["success"]:
        logger.info(f"✅ Status obtido!")
        logger.info(f"📊 Status: {result['status']}")
        logger.info(f"📅 Enviado em: {result['date_sent']}")
        if result.get('error_code'):
            logger.warning(f"⚠️  Erro: {result['error_message']} (código: {result['error_code']})")
        return True
    else:
        logger.error(f"❌ Erro ao consultar: {result['error']}")
        return False


def print_sandbox_instructions():
    """Imprime instruções para ativar sandbox (se necessário)."""
    print("\n" + "⚠️ "*30)
    print("IMPORTANTE: Sandbox WhatsApp Twilio")
    print("⚠️ "*30)
    print()
    print("Se você está usando SANDBOX (número +1 415 523 8886):")
    print()
    print("1. No seu WhatsApp, envie uma mensagem para:")
    print("   +1 415 523 8886")
    print()
    print("2. Digite exatamente:")
    print("   join <seu-codigo-sandbox>")
    print()
    print("3. Você receberá confirmação de que está conectado.")
    print()
    print("4. Depois disso, rode este teste novamente.")
    print()
    print("📖 Mais info: https://www.twilio.com/console/sms/whatsapp/sandbox")
    print("="*60)


def main():
    """Executa todos os testes."""
    print("\n" + "🚀"*30)
    print("TWILIO WHATSAPP API - TEST SUITE")
    print("🚀"*30)
    
    # Verifica se está usando sandbox
    twilio_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "")
    if "415" in twilio_number or "8886" in twilio_number:
        print_sandbox_instructions()
        response = input("\n✅ Você já ativou o sandbox? (s/n): ")
        if response.lower() != 's':
            print("\n⏸️  Ative o sandbox primeiro e rode novamente!")
            return
    
    # TEST 1: Conexão
    client = test_connection()
    if not client:
        logger.error("❌ Teste falhou na conexão")
        return
    
    # TEST 2: Mensagem de texto
    if not test_send_message(client):
        logger.error("❌ Teste 2 falhou")
        logger.info("\n💡 Dica: Se erro 63007/21408, você precisa ativar o sandbox!")
        logger.info("   Veja instruções acima.")
        return
    
    input("\n⏸️  Pressione ENTER para continuar com os próximos testes...")
    
    # TEST 3: Mensagem com mídia
    if not test_send_media(client):
        logger.error("❌ Teste 3 falhou")
        return
    
    input("\n⏸️  Pressione ENTER para finalizar...")
    
    # Sucesso!
    print("\n" + "="*60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("="*60)
    print("\n📖 Próximos passos:")
    print("1. Configure o webhook no Twilio:")
    print("   https://www.twilio.com/console/sms/whatsapp/sandbox")
    print("2. Use ngrok para testar localmente:")
    print("   ngrok http 8000")
    print("3. Inicie seu FastAPI:")
    print("   python -m uvicorn app.main:app --reload")
    print("4. Configure a URL do webhook em Twilio:")
    print("   https://seu-ngrok-url.ngrok.io/webhook/whatsapp")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Teste cancelado pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erro inesperado: {str(e)}", exc_info=True)
        sys.exit(1)
