"""
Test Script: Testar integração com Meta WhatsApp API

Uso:
    python test_whatsapp_meta.py

Requisitos:
    - Variáveis de ambiente configuradas (.env)
    - Ter credits na meta (forma de pagamento configurada)
    - Número de teste confirmado na console
"""

import os
import sys
import logging
from dotenv import load_dotenv
from app.infrastructure.messaging.whatsapp_meta_client import WhatsAppMetaClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

def test_connection():
    """Testa conexão básica com Meta API."""
    print("\n" + "="*60)
    print("TEST 1: Testar Conexão com Meta API")
    print("="*60)
    
    try:
        client = WhatsAppMetaClient()
        logger.info("✅ Cliente WhatsApp inicializado")
        
        # Testa conexão
        if client.test_connection():
            logger.info("✅ Conexão com Meta API OK!")
            return client
        else:
            logger.error("❌ Erro na conexão com Meta API")
            return None
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar: {str(e)}")
        return None


def test_send_message(client: WhatsAppMetaClient):
    """Testa envio de mensagem template (fora da janela de 24h)."""
    print("\n" + "="*60)
    print("TEST 2: Enviar Mensagem Template")
    print("="*60)
    
    # Seu número de teste (da console Meta)
    to_phone = "5561998776092"  # Use seu número aqui!
    template_name = "hello_world"
    language_code = "en_US"
    
    logger.info(f"Enviando para: {to_phone}")
    logger.info(f"Template: {template_name} ({language_code})")
    
    result = client.send_template_message(
        to_phone=to_phone,
        template_name=template_name,
        language_code=language_code
    )
    
    if result["success"]:
        logger.info(f"✅ Mensagem enviada! ID: {result['message_id']}")
        logger.info("📱 Verifique seu WhatsApp em alguns segundos...")
        return True
    else:
        logger.error(f"❌ Erro ao enviar: {result['error']}")
        return False


def test_send_buttons(client: WhatsAppMetaClient):
    """Testa envio de mensagem com botões."""
    print("\n" + "="*60)
    print("TEST 3: Enviar Mensagem com Botões")
    print("="*60)
    
    to_phone = "5561998776092"
    message = "Escolha uma opção:"
    buttons = [
        {"id": "1", "title": "Reservar Quarto"},
        {"id": "2", "title": "Estender Estadia"},
        {"id": "3", "title": "Falar com Recepção"}
    ]
    
    logger.info(f"Enviando botões para: {to_phone}")
    
    result = client.send_button_message(to_phone, message, buttons)
    
    if result["success"]:
        logger.info(f"✅ Mensagem com botões enviada! ID: {result['message_id']}")
        logger.info("💬 Clique em um dos botões...")
        return True
    else:
        logger.error(f"❌ Erro ao enviar: {result['error']}")
        return False


def test_send_list(client: WhatsAppMetaClient):
    """Testa envio de mensagem com lista."""
    print("\n" + "="*60)
    print("TEST 4: Enviar Mensagem com Lista")
    print("="*60)
    
    to_phone = "5561998776092"
    items = [
        {
            "id": "1",
            "title": "Apartamento 101",
            "description": "1 quarto, vista para a rua"
        },
        {
            "id": "2",
            "title": "Apartamento 201",
            "description": "1 quarto, vista para a piscina"
        },
        {
            "id": "3",
            "title": "Suite 301",
            "description": "2 quartos, vista privilegiada"
        }
    ]
    
    logger.info(f"Enviando lista para: {to_phone}")
    
    result = client.send_list_message(
        to_phone,
        "Escolha seu quarto:",
        "Veja as opções disponíveis",
        items
    )
    
    if result["success"]:
        logger.info(f"✅ Mensagem com lista enviada! ID: {result['message_id']}")
        logger.info("📋 Selecione uma opção na lista...")
        return True
    else:
        logger.error(f"❌ Erro ao enviar: {result['error']}")
        return False


def main():
    """Executa todos os testes."""
    print("\n" + "🚀"*30)
    print("META WHATSAPP API - TEST SUITE")
    print("🚀"*30)
    
    # TEST 1: Conexão
    client = test_connection()
    if not client:
        logger.error("❌ Teste falhou na conexão")
        return
    
    # TEST 2: Mensagem de texto
    if not test_send_message(client):
        logger.error("❌ Teste 2 falhou")
        return
    
    input("\n⏸️  Pressione ENTER para continuar com os próximos testes...")
    
    # TEST 3: Botões
    if not test_send_buttons(client):
        logger.error("❌ Teste 3 falhou")
        return
    
    input("\n⏸️  Pressione ENTER para continuar...")
    
    # TEST 4: Lista
    if not test_send_list(client):
        logger.error("❌ Teste 4 falhou")
        return
    
    # Sucesso!
    print("\n" + "="*60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("="*60)
    print("\n📖 Próximos passos:")
    print("1. Configure o webhook no Meta:")
    print("   App → Configuração → Webhooks")
    print("2. Use ngrok para testar localmente:")
    print("   ngrok http 8000")
    print("3. Inicie seu FastAPI:")
    print("   python -m uvicorn app.main:app --reload")
    print("4. Configure a URL do webhook em Meta:")
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
