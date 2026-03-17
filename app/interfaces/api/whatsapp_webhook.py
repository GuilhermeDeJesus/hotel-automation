import os
import json
import logging
import time
from fastapi import APIRouter, Request, Response, Depends
from dotenv import load_dotenv

from app.application.use_cases.handle_whatsapp_message import HandleWhatsAppMessageUseCase
from app.application.use_cases.get_saas_dashboard import GetSaaSDashboardUseCase
from app.application.dto.whatsapp_message_request_dto import WhatsAppMessageRequestDTO
from app.interfaces.di_whatsapp import get_whatsapp_message_use_case
from app.infrastructure.messaging.whatsapp_meta_client import WhatsAppMetaClient
from app.infrastructure.messaging.whatsapp_twilio_client import WhatsAppTwilioClient
from app.infrastructure.cache.redis_repository import RedisRepository
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.saas_repository_sql import SaaSRepositorySQL
from app.infrastructure.persistence.sql.hotel_config_models import HotelConfigModel

load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    return "".join(ch for ch in phone if ch.isdigit())


def _resolve_hotel_id_from_whatsapp_to(to_phone: str, session) -> str | None:
    """
    Resolve hotel_id a partir do número de WhatsApp configurado no hotel.

    Normaliza o número e busca em HotelConfigModel.whatsapp_number.
    """
    normalized = _normalize_phone(to_phone)
    if not normalized:
        return None

    config = (
        session.query(HotelConfigModel)
        .filter(HotelConfigModel.whatsapp_number.isnot(None))
        .filter(HotelConfigModel.whatsapp_number != "")
        .filter(HotelConfigModel.whatsapp_number.contains(normalized))
        .first()
    )
    if not config:
        return None
    return config.hotel_id


def _track_saas(
    phone: str,
    source: str,
    event_type: str,
    success: bool = True,
    response_time_ms: int | None = None,
    details: dict | None = None,
    hotel_id: str | None = None,
) -> None:
    if not phone:
        return

    session = SessionLocal()
    should_invalidate_cache = False
    try:
        repo = SaaSRepositorySQL(session)
        # hotel_id é obrigatório para leads; se não vier, só registra evento
        if hotel_id:
            if event_type == "inbound_message":
                repo.touch_lead(hotel_id=hotel_id, phone=phone, source=source, stage="NEW")
            elif event_type == "outbound_message":
                repo.touch_lead(hotel_id=hotel_id, phone=phone, source=source, stage="ENGAGED")

        repo.track_event(
            phone=phone,
            source=source,
            event_type=event_type,
            success=success,
            response_time_ms=response_time_ms,
            details=details,
        )
        if hotel_id:
            repo.sync_lead_stage_from_reservation(phone)
            should_invalidate_cache = True
    except Exception as exc:
        logger.warning(f"⚠️ Falha ao registrar evento SaaS: {exc}")
    finally:
        session.close()

    if should_invalidate_cache:
        try:
            deleted = GetSaaSDashboardUseCase.invalidate_analytics_cache(RedisRepository())
            if deleted:
                logger.info(f"🧹 Cache SaaS invalidado ({deleted} chaves).")
        except Exception as exc:
            logger.warning(f"⚠️ Falha ao invalidar cache SaaS: {exc}")

# Inicializa clientes WhatsApp
try:
    whatsapp_client = WhatsAppMetaClient()
    logger.info("✅ WhatsApp Meta Client inicializado")
except Exception as e:
    logger.error(f"❌ Erro ao inicializar WhatsApp Meta: {str(e)}")
    whatsapp_client = None

try:
    whatsapp_twilio_client = WhatsAppTwilioClient()
    logger.info("✅ WhatsApp Twilio Client inicializado")
except Exception as e:
    logger.error(f"❌ Erro ao inicializar WhatsApp Twilio: {str(e)}")
    whatsapp_twilio_client = None


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


# ==================== WEBHOOK RECEIVER (META) ====================
@router.post("/webhook/whatsapp")
async def receive_whatsapp_message(
    request: Request,
    use_case: HandleWhatsAppMessageUseCase = Depends(get_whatsapp_message_use_case),
):
    """
    Recebe mensagens do WhatsApp via Meta Cloud API.
    """
    
    try:
        body = await request.json()
        logger.info(f"📨 Webhook Meta recebido")
        
        # Valida se é realmente do WhatsApp
        if body.get("object") != "whatsapp_business_account":
            logger.warning(f"⚠️  Objeto ignorado: {body.get('object')}")
            return {"status": "ignored"}
        
        session = SessionLocal()
        try:
            # Resolve hotel_id a partir do número de destino (Meta: metadata.phone_number_id ou value.metadata)
            hotel_id: str | None = None

            # Meta normalmente fornece phone_number_id em value.metadata
            entry_list = body.get("entry", [])
            for entry in entry_list:
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    metadata = value.get("metadata", {})
                    to_phone_raw = metadata.get("display_phone_number") or metadata.get("phone_number_id") or ""
                    if to_phone_raw and not hotel_id:
                        hotel_id = _resolve_hotel_id_from_whatsapp_to(to_phone_raw, session)

                    # Processa mensagens recebidas
                    messages = value.get("messages", [])
                    for message in messages:
                        await _handle_incoming_message(message, use_case, hotel_id)
                    # Processa status de entrega
                    statuses = value.get("statuses", [])
                    for status in statuses:
                        _handle_message_status(status)
        finally:
            session.close()
        
        return {"status": "ok"}
    
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON inválido: {str(e)}")
        return {"status": "error", "error": "Invalid JSON"}
    except Exception as e:
        logger.error(f"❌ Erro processando webhook Meta: {str(e)}", exc_info=True)
        return {"status": "error", "error": str(e)}


# ==================== WEBHOOK RECEIVER (TWILIO) ====================
@router.post("/webhook/whatsapp/twilio")
async def receive_twilio_whatsapp_message(
    request: Request,
    use_case: HandleWhatsAppMessageUseCase = Depends(get_whatsapp_message_use_case),
):
    """
    Recebe mensagens do WhatsApp via Twilio API.
    Responde automaticamente usando o bot."""
    
    if not whatsapp_twilio_client:
        logger.error("❌ Twilio client não inicializado")
        return Response(status_code=200)
    
    try:
        # Twilio envia form-data, não JSON
        form_data = await request.form()
        
        # Extrai dados da mensagem
        from_phone_raw = form_data.get("From", "").replace("whatsapp:", "")
        from_phone = _normalize_phone(from_phone_raw)
        to_phone_raw = form_data.get("To", "").replace("whatsapp:", "")
        message_body = form_data.get("Body", "")
        message_sid = form_data.get("MessageSid", "")
        num_media = int(form_data.get("NumMedia", 0))
        
        logger.info(f"📱 [TWILIO] Mensagem de {from_phone} | SID: {message_sid}")
        logger.info(f"📝 [TWILIO] Conteúdo: '{message_body}'")
        
        if num_media > 0:
            media_url = form_data.get("MediaUrl0", "")
            logger.info(f"📎 [TWILIO] Mídia: {media_url}")

        # Resolve hotel_id a partir do número de destino Twilio (To)
        session = SessionLocal()
        try:
            hotel_id = _resolve_hotel_id_from_whatsapp_to(to_phone_raw, session)
        finally:
            session.close()

        _track_saas(
            phone=from_phone,
            source="twilio",
            event_type="inbound_message",
            details={"message_sid": message_sid},
            hotel_id=hotel_id,
        )
        
        # Processa a mensagem e gera resposta
        # Quando num_media > 0, Body pode vir vazio (ex: imagem sem legenda)
        has_media = num_media > 0
        started_at = time.perf_counter()
        response_dto = use_case.execute(
            hotel_id=hotel_id,
            request_dto=WhatsAppMessageRequestDTO(
                phone=from_phone,
                message=message_body,
                source="twilio",
                has_media=has_media,
            )
        )
        
        # Envia resposta via Twilio
        result = whatsapp_twilio_client.send_text_message(from_phone, response_dto.reply)
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        
        if result["success"]:
            logger.info(f"✅ [TWILIO] Resposta enviada para {from_phone}")
        else:
            logger.error(f"❌ [TWILIO] Erro ao enviar: {result}")

        _track_saas(
            phone=from_phone,
            source="twilio",
            event_type="outbound_message",
            success=bool(result.get("success")),
            response_time_ms=elapsed_ms,
            details={"message_sid": message_sid},
            hotel_id=hotel_id,
        )
        
        # Twilio precisa de status 200 para confirmar
        return Response(status_code=200)
    
    except Exception as e:
        logger.error(f"❌ Erro processando webhook Twilio: {str(e)}", exc_info=True)
        return Response(status_code=200)


# ==================== MESSAGE HANDLERS ====================
async def _handle_incoming_message(
    message: dict,
    use_case: HandleWhatsAppMessageUseCase,
    hotel_id: str | None,
):
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
    from_phone = _normalize_phone(message.get("from"))
    timestamp = message.get("timestamp")
    msg_type = message.get("type")
    
    logger.info(f"📱 Mensagem de {from_phone} | tipo: {msg_type} | id: {message_id}")
    
    # Marca como lida (double blue check)
    whatsapp_client.mark_as_read(message_id)
    
    # Extrai conteúdo baseado no tipo
    content = _extract_message_content(message, msg_type)
    has_media = msg_type in ("image", "document", "audio", "video")

    logger.info(f"📝 Conteúdo: '{content}' | has_media: {has_media}")

    # Processa a mensagem
    try:
        _track_saas(
            phone=from_phone,
            source="meta",
            event_type="inbound_message",
            details={"message_id": message_id, "type": msg_type},
        )

        started_at = time.perf_counter()
        response_dto = use_case.execute(
            hotel_id=hotel_id,
            request_dto=WhatsAppMessageRequestDTO(
                phone=from_phone,
                message=content,
                source="meta",
                has_media=has_media,
            )
        )
        
        # Envia resposta via WhatsApp
        result = whatsapp_client.send_text_message(from_phone, response_dto.reply)
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        
        if result["success"]:
            logger.info(f"✅ Resposta enviada para {from_phone}")
        else:
            logger.error(f"❌ Erro ao enviar resposta: {result['error']}")

        _track_saas(
            phone=from_phone,
            source="meta",
            event_type="outbound_message",
            success=bool(result.get("success")),
            response_time_ms=elapsed_ms,
            details={"message_id": message_id, "type": msg_type},
        )
    
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