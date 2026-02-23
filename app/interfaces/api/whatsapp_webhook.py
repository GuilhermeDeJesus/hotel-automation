import os
import json
import logging
from fastapi import APIRouter, Request, Response, Depends
from pydantic import BaseModel
from dotenv import load_dotenv

from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
from app.application.dto.checkin_request_dto import CheckinRequestDTO
from app.interfaces.dependencies import get_checkin_use_case
from app.infrastructure.messaging.whatsapp_meta_client import WhatsAppMetaClient

load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)

# Inicializa cliente WhatsApp
try:
    whatsapp_client = WhatsAppMetaClient()
    logger.info("✅ WhatsApp Meta Client inicializado")
except Exception as e:
    logger.error(f"❌ Erro ao inicializar WhatsApp: {str(e)}")
    whatsapp_client = None


# ==================== WEBHOOK VERIFICATION ====================
@router.get("/webhook/whatsapp")
async def verify_webhook(request: Request):
    """
    Meta envia GET com query params para verificar webhook.
    Você responde com o challenge para confirmar que é seu webhook.
    
    Isso acontece quando você configura a URL do webhook em:
    https://developers.facebook.com/ → Seu App → Configuração → Webhooks
    """
    
    verify_token = os.getenv("WEBHOOK_VERIFY_TOKEN", "seu_token_secreto")
    
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    logger.info(f"🔐 Webhook verification request: mode={mode}, token_match={token == verify_token}")
    
    if mode == "subscribe" and token == verify_token:
        logger.info("✅ Webhook verificado com sucesso!")
        return Response(content=challenge, status_code=200)
    else:
        logger.error(f"❌ Webhook verification falhou! Token esperado: {verify_token}, recebido: {token}")
        return Response(content="Unauthorized", status_code=403)


# ==================== WEBHOOK RECEIVER ====================
@router.post("/webhook/whatsapp")
async def receive_whatsapp_message(
    request: Request,
    use_case: CheckInViaWhatsAppUseCase = Depends(get_checkin_use_case)
):
    """
    Recebe mensagens do WhatsApp via Meta Cloud API.
    
    Meta envia POST com a struct:
    {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [...],
                    "statuses": [...]
                }
            }]
        }]
    }
    """
    
    try:
        body = await request.json()
        logger.info(f"📨 Webhook recebido: {json.dumps(body, indent=2)}")
        
        # Valida se é realmente do WhatsApp
        if body.get("object") != "whatsapp_business_account":
            logger.warning(f"⚠️  Objeto ignorado: {body.get('object')}")
            return {"status": "ignored"}
        
        # Processa cada entrada
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # Processa mensagens recebidas
                messages = value.get("messages", [])
                for message in messages:
                    await _handle_incoming_message(message, use_case)
                
                # Processa status de entrega (opcional - para logging)
                statuses = value.get("statuses", [])
                for status in statuses:
                    _handle_message_status(status)
        
        return {"status": "ok"}
    
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON inválido: {str(e)}")
        return {"status": "error", "error": "Invalid JSON"}
    except Exception as e:
        logger.error(f"❌ Erro processando webhook: {str(e)}", exc_info=True)
        return {"status": "error", "error": str(e)}


# ==================== MESSAGE HANDLERS ====================
async def _handle_incoming_message(message: dict, use_case: CheckInViaWhatsAppUseCase):
    """
    Processa mensagem recebida do WhatsApp.
    
    Estrutura:
    {
        "id": "wamid.xxx",
        "from": "5561998776092",
        "type": "text" | "button" | "interactive" | etc,
        "timestamp": "1234567890",
        "text": {"body": "..."},
        ...
    }
    """
    
    if not whatsapp_client:
        logger.error("❌ WhatsApp client não inicializado")
        return
    
    message_id = message.get("id")
    from_phone = message.get("from")
    timestamp = message.get("timestamp")
    msg_type = message.get("type")
    
    logger.info(f"📱 Mensagem de {from_phone} | tipo: {msg_type} | id: {message_id}")
    
    # Marca como lida (double blue check)
    whatsapp_client.mark_as_read(message_id)
    
    # Extrai conteúdo baseado no tipo
    content = _extract_message_content(message, msg_type)
    
    logger.info(f"📝 Conteúdo: '{content}'")
    
    # Processa a mensagem
    try:
        reply = await _generate_reply(from_phone, content, use_case)
        
        # Envia resposta via WhatsApp
        result = whatsapp_client.send_text_message(from_phone, reply)
        
        if result["success"]:
            logger.info(f"✅ Resposta enviada para {from_phone}")
        else:
            logger.error(f"❌ Erro ao enviar resposta: {result['error']}")
    
    except Exception as e:
        logger.error(f"❌ Erro ao processar mensagem: {str(e)}", exc_info=True)
        
        # Notifica erro ao usuário
        try:
            whatsapp_client.send_text_message(
                from_phone,
                "Desculpa, ocorreu um erro. Tente novamente mais tarde."
            )
        except:
            pass


def _extract_message_content(message: dict, msg_type: str) -> str:
    """Extrai conteúdo da mensagem baseado no tipo."""
    
    if msg_type == "text":
        return message.get("text", {}).get("body", "")
    
    elif msg_type == "button":
        # Quando usuário clica num botão
        return message.get("button", {}).get("text", "")
    
    elif msg_type == "interactive":
        # Resposta interativa (menu, lista, etc)
        interactive = message.get("interactive", {})
        
        # Resposta de botão
        button_reply = interactive.get("button_reply", {})
        if button_reply:
            return button_reply.get("title", "")
        
        # Resposta de lista
        list_reply = interactive.get("list_reply", {})
        if list_reply:
            return list_reply.get("title", "")
        
        return "[interactive]"
    
    else:
        # Para outros tipos (imagem, arquivo, etc)
        return f"[{msg_type.upper()}]"


async def _generate_reply(from_phone: str, content: str, use_case: CheckInViaWhatsAppUseCase) -> str:
    """
    Gera resposta para a mensagem.
    
    Aqui você implementa sua lógica de IA/fluxo.
    """
    
    content_lower = content.lower().strip()
    
    # Exemplo 1: Se pedir check-in
    if "check-in" in content_lower or "checkin" in content_lower:
        try:
            response_dto = use_case.execute(
                CheckinRequestDTO(phone=from_phone)
            )
            return response_dto.message
        except Exception as e:
            logger.error(f"❌ Erro no check-in: {str(e)}")
            return f"Erro ao processar check-in: {str(e)}"
    
    # Exemplo 2: Se pedir informações
    elif "reserva" in content_lower or "booking" in content_lower:
        return "Para fazer uma reserva, envie: RESERVA [datas] [quartos]"
    
    # Padrão: Echo da mensagem
    else:
        return f"Recebi sua mensagem: '{content}'\n\nComo posso ajudar?"


def _handle_message_status(status: dict):
    """
    Processa status de entrega de mensagem.
    
    Tipos: "sent", "delivered", "read", "failed"
    """
    
    message_id = status.get("id")
    status_type = status.get("status")
    recipient = status.get("recipient_id")
    timestamp = status.get("timestamp")
    
    logger.info(f"📊 Status: {message_id} → {status_type} (destinatário: {recipient})")
    
    # Você pode guardar isso no banco para rastreamento
    # Exemplo: logs_db.insert({"message_id": message_id, "status": status_type, "recipient": recipient})