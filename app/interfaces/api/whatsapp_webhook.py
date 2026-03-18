import os
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from datetime import time as dt_time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
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
from app.infrastructure.persistence.sql.hotel_config_models import HotelConfigModel, HotelNotificationModel

load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)

_IDEMPOTENCY_REPLY_TTL_SECONDS = 14 * 24 * 3600
_IDEMPOTENCY_DONE_TTL_SECONDS = 14 * 24 * 3600
_IDEMPOTENCY_LOCK_TTL_SECONDS = 60


def _idempotency_done_key(hotel_id: str | None, source: str, message_id: str) -> str:
    hid = hotel_id or "unknown"
    return f"whatsapp:idempotency:done:{hid}:{source}:{message_id}"


def _idempotency_reply_key(hotel_id: str | None, source: str, message_id: str) -> str:
    hid = hotel_id or "unknown"
    return f"whatsapp:idempotency:reply:{hid}:{source}:{message_id}"


def _idempotency_lock_key(hotel_id: str | None, source: str, message_id: str) -> str:
    hid = hotel_id or "unknown"
    return f"whatsapp:idempotency:lock:{hid}:{source}:{message_id}"


def _acquire_redis_lock(redis_repo: RedisRepository, lock_key: str) -> str | None:
    """
    Acquire an atomic Redis lock using SET NX.
    Returns the lock token if acquired, else None.
    """
    token = str(uuid.uuid4())
    ok = redis_repo.client.set(
        lock_key,
        token,
        nx=True,
        ex=_IDEMPOTENCY_LOCK_TTL_SECONDS,
    )
    return token if ok else None


def _release_redis_lock(redis_repo: RedisRepository, lock_key: str, token: str) -> None:
    """
    Release lock only if the token matches (Lua script for safety).
    """
    try:
        lua = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        redis_repo.client.eval(lua, 1, lock_key, token)
    except Exception:
        # Don't fail webhook because of lock release issues.
        pass


def _normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    return "".join(ch for ch in phone if ch.isdigit())


def _extract_twilio_message_body(form_data: object) -> str:
    """
    Extrai texto da mensagem do Twilio (WhatsApp).

    Em interações (botões/listas), o Twilio pode preencher campos como:
    - ButtonText / ButtonPayload
    - ListItemText / ListItemPayload
    enquanto o campo `Body` pode vir vazio.
    """
    # FormData é um objeto tipo dict-like; usamos getattr/get por segurança.
    get = getattr(form_data, "get", None)
    if not callable(get):
        return ""

    body = get("Body") or ""
    button_text = get("ButtonText") or ""
    list_item_text = get("ListItemText") or ""
    list_title = get("ListTitle") or ""
    button_payload = get("ButtonPayload") or ""
    list_item_payload = get("ListItemPayload") or ""

    # Heurística: se alguma das partes tiver intenção explícita (foto/fotos),
    # priorizamos essa string para garantir que o bot acione o fluxo correto.
    photo_keywords = ("foto", "fotos", "imagem", "imagens")
    candidates = [button_text, list_item_text, body, list_title, button_payload, list_item_payload]
    for c in candidates:
        c_str = str(c or "").strip()
        c_lower = c_str.lower()
        if c_str and any(kw in c_lower for kw in photo_keywords):
            return c_str

    if str(button_text).strip():
        return str(button_text).strip()
    if str(list_item_text).strip():
        return str(list_item_text).strip()
    if not str(body).strip():
        return str(button_payload or list_item_payload or "").strip()
    return str(body).strip()


def _parse_hhmm(value: str | None) -> dt_time | None:
    if not value:
        return None
    try:
        parts = str(value).split(":")
        if len(parts) < 2:
            return None
        hour = int(parts[0])
        minute = int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None
        return dt_time(hour=hour, minute=minute)
    except Exception:
        return None


def _interval_contains(now_t: dt_time, start_t: dt_time, end_t: dt_time) -> bool:
    """
    Intervalo diário com suporte a intervalo que cruza meia-noite.
    Semântica: start inclusive, end exclusivo.
    """
    if start_t == end_t:
        # Configuração estranha, mas interpretamos como "sempre ativo".
        return True
    if start_t < end_t:
        return start_t <= now_t < end_t
    # Cruza meia-noite (ex: 22:00 -> 08:00)
    return now_t >= start_t or now_t < end_t


def _next_occurrence_after(now_dt: datetime, target_t: dt_time) -> datetime:
    """
    Retorna o próximo datetime (>= agora se o target_t cair no futuro; caso contrário, soma 1 dia).
    """
    candidate = now_dt.replace(
        hour=target_t.hour,
        minute=target_t.minute,
        second=0,
        microsecond=0,
    )
    if candidate <= now_dt:
        candidate = candidate + timedelta(days=1)
    return candidate


def _build_out_of_hours_reply(next_time_str: str | None, contact_phone: str | None) -> str:
    # Mensagem curta e previsível (reduz frustração).
    if next_time_str:
        reply = f"Olá! Estamos fora do atendimento agora. Voltamos às {next_time_str}."
    else:
        reply = "Olá! Estamos fora do atendimento agora."

    if contact_phone:
        reply += f" Se precisar, fale com a equipe pelo telefone: {contact_phone}."
    else:
        reply += " Se precisar, fale com a equipe por telefone."
    return reply


def _get_out_of_hours_reply_text(hotel_id: str | None) -> str | None:
    """
    Retorna o texto da resposta padrão quando estamos fora do atendimento/quiet hours.
    Retorna `None` quando o bot pode responder normalmente.
    """
    if not hotel_id:
        return None

    session = SessionLocal()
    config: HotelConfigModel | None = None
    notifications: HotelNotificationModel | None = None
    try:
        config = session.query(HotelConfigModel).filter_by(hotel_id=hotel_id).first()
        notifications = session.query(HotelNotificationModel).filter_by(hotel_id=hotel_id).first()
    finally:
        session.close()

    if not config:
        return None

    tz_name = None
    if notifications and getattr(notifications, "notification_timezone", None):
        tz_name = notifications.notification_timezone
    elif getattr(config, "timezone", None):
        tz_name = config.timezone
    else:
        tz_name = "UTC"

    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")

    now_local = datetime.now(tz)
    now_t = dt_time(hour=now_local.hour, minute=now_local.minute)

    contact_phone = getattr(config, "contact_phone", None)

    # 1) Whatsapp business hours (prioridade maior que quiet hours).
    business_hours = getattr(config, "whatsapp_business_hours", None)
    business_start_t: dt_time | None = None
    business_end_t: dt_time | None = None
    if isinstance(business_hours, dict):
        business_start_t = _parse_hhmm(business_hours.get("start"))
        business_end_t = _parse_hhmm(business_hours.get("end"))

    if business_start_t and business_end_t:
        within_business = _interval_contains(now_t, business_start_t, business_end_t)
        if not within_business:
            next_open_dt = _next_occurrence_after(now_local, business_start_t)
            next_open_str = next_open_dt.strftime("%H:%M")
            return _build_out_of_hours_reply(next_open_str, contact_phone)

    # 2) Quiet hours (se habilitado).
    quiet_enabled = False
    quiet_hours_start_t: dt_time | None = None
    quiet_hours_end_t: dt_time | None = None
    if notifications:
        quiet_enabled = bool(getattr(notifications, "quiet_hours_enabled", False))
        quiet_hours_start_t = _parse_hhmm(getattr(notifications, "quiet_hours_start", None))
        quiet_hours_end_t = _parse_hhmm(getattr(notifications, "quiet_hours_end", None))

    if quiet_enabled and quiet_hours_start_t and quiet_hours_end_t:
        within_quiet = _interval_contains(now_t, quiet_hours_start_t, quiet_hours_end_t)
        if within_quiet:
            next_quiet_end_dt = _next_occurrence_after(now_local, quiet_hours_end_t)
            next_quiet_end_str = next_quiet_end_dt.strftime("%H:%M")
            return _build_out_of_hours_reply(next_quiet_end_str, contact_phone)

    return None


def _get_whatsapp_rate_limit_debounce_seconds(hotel_id: str | None) -> float:
    """
    Retorna intervalo mínimo (debounce) entre mensagens do mesmo telefone.
    Usa `HotelConfigModel.rate_limit_config` quando disponível.
    """
    if not hotel_id:
        return 0.0

    # Default conservador para evitar spam.
    default_debounce = 2.0

    session = SessionLocal()
    config: HotelConfigModel | None = None
    try:
        config = session.query(HotelConfigModel).filter_by(hotel_id=hotel_id).first()
    finally:
        session.close()

    rate_limit_config = getattr(config, "rate_limit_config", None) if config else None
    if not isinstance(rate_limit_config, dict):
        return default_debounce

    # Permite que a config venha aninhada por canal.
    whatsapp_config = rate_limit_config.get("whatsapp", rate_limit_config)
    if not isinstance(whatsapp_config, dict):
        whatsapp_config = rate_limit_config

    candidate_keys = [
        "debounce_seconds",
        "min_interval_seconds",
        "min_seconds_between_messages",
        "cooldown_seconds",
    ]
    for key in candidate_keys:
        if key in whatsapp_config:
            raw_val = whatsapp_config.get(key)
            try:
                val = float(raw_val)
                if val > 0:
                    return val
            except (TypeError, ValueError):
                pass

    return default_debounce


def _serialize_meta_outbound(response_dto: object) -> str:
    """
    Serializa payload para cache idempotente (Meta).

    Mantém compatibilidade: se for "text", salva apenas a string `reply`.
    """
    message_type = getattr(response_dto, "message_type", "text") or "text"
    reply = getattr(response_dto, "reply", "") or ""

    if message_type == "text":
        return reply

    payload = {
        "message_type": message_type,
        "reply": reply,
        "buttons": getattr(response_dto, "buttons", []) or [],
        "list_header": getattr(response_dto, "list_header", None),
        "list_body": getattr(response_dto, "list_body", None),
        "list_items": getattr(response_dto, "list_items", []) or [],
        "media_ids": getattr(response_dto, "media_ids", []) or [],
        "media_caption": getattr(response_dto, "media_caption", None),
    }
    return json.dumps(payload, ensure_ascii=False)


def _try_deserialize_meta_cached_reply(cached_value: str) -> dict | None:
    """
    Tenta interpretar o cache como JSON (payload interativo).
    Retorna dict se for interativo e estruturado; caso contrário, None.
    """
    try:
        parsed = json.loads(cached_value)
        if isinstance(parsed, dict) and parsed.get("message_type"):
            return parsed
    except Exception:
        pass
    return None


def _serialize_twilio_outbound(response_dto: object) -> str:
    """
    Serializa payload para cache idempotente (Twilio).

    Compatibilidade:
    - Se message_type == "text": armazena só a string `reply`
    - Se for mídia/interativo: armazena JSON com campos necessários.
    """
    message_type = getattr(response_dto, "message_type", "text") or "text"
    reply = getattr(response_dto, "reply", "") or ""
    if message_type == "text":
        return reply

    payload = {
        "message_type": message_type,
        "reply": reply,
        "buttons": getattr(response_dto, "buttons", []) or [],
        "media_ids": getattr(response_dto, "media_ids", []) or [],
        "media_caption": getattr(response_dto, "media_caption", None),
    }
    return json.dumps(payload, ensure_ascii=False)


def _try_deserialize_twilio_cached_reply(cached_value: str) -> dict | None:
    if not cached_value:
        return None
    try:
        parsed = json.loads(cached_value)
        if isinstance(parsed, dict) and parsed.get("message_type"):
            return parsed
    except Exception:
        pass
    return None


def _send_meta_outbound(
    whatsapp_client: WhatsAppMetaClient,
    to_phone: str,
    response_dto: object,
    public_media_base_url: str,
    hotel_id: str,
) -> dict:
    message_type = getattr(response_dto, "message_type", "text") or "text"
    reply = getattr(response_dto, "reply", "") or ""
    media_ids = getattr(response_dto, "media_ids", []) or []
    media_caption = getattr(response_dto, "media_caption", None)

    if message_type == "button":
        buttons = getattr(response_dto, "buttons", []) or []
        if buttons:
            return whatsapp_client.send_button_message(to_phone, reply, buttons)

    if message_type == "list":
        list_items = getattr(response_dto, "list_items", []) or []
        if list_items:
            return whatsapp_client.send_list_message(
                to_phone,
                header=getattr(response_dto, "list_header", "") or "",
                body=getattr(response_dto, "list_body", None) or reply,
                items=list_items,
            )

    if message_type in ("photo", "photo_set"):
        if not media_ids:
            return whatsapp_client.send_text_message(to_phone, reply)

        # Envia mídia(s) primeiro.
        caption_for_media = media_caption if media_caption is not None else ""
        last_result: dict = {"success": False, "error": "no-media-result"}
        all_success = True
        for idx, media_id in enumerate(media_ids[:3]):
            url = f"{public_media_base_url.rstrip('/')}/saas/hotel/{hotel_id}/media-public/{media_id}"
            # Para "photo_set" tentamos manter caption constante.
            cap = caption_for_media
            # Se vier reply embutido como legenda, ainda mantemos fallback.
            if message_type == "photo" and cap == "":
                cap = reply
            if message_type == "photo_set" and cap == "":
                cap = ""
            last_result = whatsapp_client.send_image_message(to_phone, cap, url)
            all_success = all_success and bool(last_result.get("success"))

        if not all_success:
            return last_result

        # Para photo_set, depois perguntamos a preferência com botões/texto.
        if message_type == "photo_set":
            buttons = getattr(response_dto, "buttons", []) or []
            if buttons:
                pref_reply = reply or "Qual prefere? (1/2/3)"
                return whatsapp_client.send_button_message(to_phone, pref_reply, buttons)
            if reply:
                return whatsapp_client.send_text_message(to_phone, reply)
        return last_result

    return whatsapp_client.send_text_message(to_phone, reply)


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
        if hotel_id:
            if event_type == "inbound_message":
                repo.touch_lead(hotel_id=hotel_id, phone=phone, source=source, stage="NEW")
            elif event_type == "outbound_message":
                repo.touch_lead(hotel_id=hotel_id, phone=phone, source=source, stage="ENGAGED")
            repo.track_event(
                hotel_id=hotel_id,
                phone=phone,
                source=source,
                event_type=event_type,
                success=success,
                response_time_ms=response_time_ms,
                details=details,
            )
            repo.sync_lead_stage_from_reservation(hotel_id=hotel_id, phone=phone)
            should_invalidate_cache = True
    except Exception as exc:
        logger.warning(f"⚠️ Falha ao registrar evento SaaS: {exc}")
    finally:
        session.close()

    if should_invalidate_cache:
        try:
            deleted = GetSaaSDashboardUseCase.invalidate_analytics_cache(
                RedisRepository(), hotel_id=hotel_id
            )
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

        public_media_base_url = str(request.base_url).rstrip("/")
        
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
                        await _handle_incoming_message(
                            message,
                            use_case,
                            hotel_id,
                            public_media_base_url=public_media_base_url,
                        )
                    # Processa status de entrega
                    statuses = value.get("statuses", [])
                    for status in statuses:
                        _handle_message_status(status, hotel_id)
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
        message_body = _extract_twilio_message_body(form_data)
        message_sid = form_data.get("MessageSid", "")
        num_media = int(form_data.get("NumMedia", 0))
        
        logger.info(f"📱 [TWILIO] Mensagem de {from_phone} | SID: {message_sid}")
        logger.info(f"📝 [TWILIO] Conteúdo: '{message_body}'")

        public_media_base_url = str(request.base_url).rstrip("/")
        
        if num_media > 0:
            media_url = form_data.get("MediaUrl0", "")
            logger.info(f"📎 [TWILIO] Mídia: {media_url}")

        # Resolve hotel_id a partir do número de destino Twilio (To)
        session = SessionLocal()
        try:
            hotel_id = _resolve_hotel_id_from_whatsapp_to(to_phone_raw, session)
        finally:
            session.close()

        if not hotel_id:
            logger.warning(
                f"⚠️ [TWILIO] hotel_id não resolvido (to_phone={to_phone_raw}). Ignorando processamento para evitar namespaces 'None'."
            )
            return Response(status_code=200)

        source = "twilio"
        if message_sid:
            redis_repo = RedisRepository()
            done_key = _idempotency_done_key(hotel_id, source, message_sid)
            reply_key = _idempotency_reply_key(hotel_id, source, message_sid)
            lock_key = _idempotency_lock_key(hotel_id, source, message_sid)

            if redis_repo.client.exists(done_key):
                logger.info(f"🔁 [TWILIO] Ignorando duplicado (done): {message_sid}")
                return Response(status_code=200)

            token = _acquire_redis_lock(redis_repo, lock_key)
            if not token:
                logger.info(f"⏳ [TWILIO] Ignorando duplicado (lock): {message_sid}")
                return Response(status_code=200)

            try:
                cached_reply = redis_repo.client.get(reply_key)
                if cached_reply:
                    reply_text = (
                        cached_reply.decode("utf-8")
                        if isinstance(cached_reply, (bytes, bytearray))
                        else str(cached_reply)
                    )
                    started_at = time.perf_counter()
                    cached_payload = _try_deserialize_twilio_cached_reply(reply_text)

                    result = {"success": False}
                    if cached_payload:
                        message_type = cached_payload.get("message_type") or "text"
                        reply = cached_payload.get("reply") or ""
                        media_ids = cached_payload.get("media_ids", []) or []
                        media_caption = cached_payload.get("media_caption") or ""

                        all_success = True
                        if message_type == "photo" and media_ids:
                            media_id = media_ids[0]
                            url = f"{public_media_base_url.rstrip('/')}/saas/hotel/{hotel_id}/media-public/{media_id}"
                            send_res = whatsapp_twilio_client.send_media_message(
                                from_phone,
                                message=media_caption or reply,
                                media_url=url,
                            )
                            all_success = bool(send_res.get("success"))
                            result = send_res
                            if reply and not media_caption:
                                # Se reply vier como texto/caption, já foi enviado como legenda.
                                pass
                            elif reply:
                                # Opcionalmente manda reply como texto adicional.
                                text_res = whatsapp_twilio_client.send_text_message(from_phone, reply)
                                all_success = all_success and bool(text_res.get("success"))
                                result = text_res

                        elif message_type == "photo_set" and media_ids:
                            for media_id in media_ids[:3]:
                                url = f"{public_media_base_url.rstrip('/')}/saas/hotel/{hotel_id}/media-public/{media_id}"
                                send_res = whatsapp_twilio_client.send_media_message(
                                    from_phone,
                                    message=media_caption or "",
                                    media_url=url,
                                )
                                all_success = all_success and bool(send_res.get("success"))
                                result = send_res
                            if reply:
                                text_res = whatsapp_twilio_client.send_text_message(from_phone, reply)
                                all_success = all_success and bool(text_res.get("success"))
                                result = text_res

                        else:
                            # fallback: trata como texto
                            result = whatsapp_twilio_client.send_text_message(from_phone, reply_text)

                        # Padroniza sucesso para o idempotency flag.
                        if not all_success:
                            result["success"] = False
                    else:
                        result = whatsapp_twilio_client.send_text_message(from_phone, reply_text)

                    elapsed_ms = int((time.perf_counter() - started_at) * 1000)

                    _track_saas(
                        phone=from_phone,
                        source="twilio",
                        event_type="outbound_message",
                        success=bool(result.get("success")),
                        response_time_ms=elapsed_ms,
                        details={"message_sid": message_sid},
                        hotel_id=hotel_id,
                    )

                    if result.get("success"):
                        redis_repo.client.set(done_key, 1, ex=_IDEMPOTENCY_DONE_TTL_SECONDS)
                        redis_repo.client.delete(reply_key)
                    return Response(status_code=200)

                _track_saas(
                    phone=from_phone,
                    source="twilio",
                    event_type="inbound_message",
                    details={"message_sid": message_sid},
                    hotel_id=hotel_id,
                )

                out_of_hours_reply = _get_out_of_hours_reply_text(hotel_id)
                if out_of_hours_reply:
                    started_at = time.perf_counter()
                    redis_repo.client.set(
                        reply_key,
                        out_of_hours_reply,
                        ex=_IDEMPOTENCY_REPLY_TTL_SECONDS,
                    )
                    result = whatsapp_twilio_client.send_text_message(
                        from_phone, out_of_hours_reply
                    )
                    elapsed_ms = int((time.perf_counter() - started_at) * 1000)

                    if result.get("success"):
                        logger.info(
                            f"⏸️ [TWILIO] Resposta fora do atendimento enviada para {from_phone}"
                        )
                        redis_repo.client.set(
                            done_key, 1, ex=_IDEMPOTENCY_DONE_TTL_SECONDS
                        )
                        redis_repo.client.delete(reply_key)
                    else:
                        logger.error(
                            f"❌ [TWILIO] Erro ao enviar resposta fora do atendimento: {result}"
                        )

                    _track_saas(
                        phone=from_phone,
                        source="twilio",
                        event_type="outbound_message",
                        success=bool(result.get("success")),
                        response_time_ms=elapsed_ms,
                        details={"message_sid": message_sid, "out_of_hours": True},
                        hotel_id=hotel_id,
                    )
                    return Response(status_code=200)

                debounce_seconds = _get_whatsapp_rate_limit_debounce_seconds(hotel_id)
                if debounce_seconds and debounce_seconds > 0:
                    now_ts = time.time()
                    rate_last_key = f"whatsapp:rate_limit:last:{hotel_id or 'unknown'}:{from_phone}"
                    last_ts_raw = redis_repo.client.get(rate_last_key)
                    last_ts = None
                    if last_ts_raw:
                        try:
                            last_ts = float(last_ts_raw)
                        except (TypeError, ValueError):
                            last_ts = None

                    redis_repo.client.set(
                        rate_last_key, str(now_ts), ex=int(debounce_seconds) + 30
                    )

                    if last_ts is not None and now_ts - last_ts < debounce_seconds:
                        warn_key = f"whatsapp:rate_limit:warned:{hotel_id or 'unknown'}:{from_phone}"
                        should_warn = not bool(redis_repo.client.exists(warn_key))
                        if should_warn:
                            redis_repo.client.set(
                                warn_key, 1, ex=int(debounce_seconds) + 10
                            )
                            warn_text = (
                                "Estou processando sua solicitação. "
                                "Por favor, aguarde alguns segundos e tente novamente."
                            )
                            started_at = time.perf_counter()
                            result = whatsapp_twilio_client.send_text_message(
                                from_phone, warn_text
                            )
                            elapsed_ms = int(
                                (time.perf_counter() - started_at) * 1000
                            )

                            _track_saas(
                                phone=from_phone,
                                source="twilio",
                                event_type="outbound_message",
                                success=bool(result.get("success")),
                                response_time_ms=elapsed_ms,
                                details={
                                    "message_sid": message_sid,
                                    "out_of_hours": False,
                                    "rate_limited": True,
                                },
                                hotel_id=hotel_id,
                            )

                            if result.get("success"):
                                redis_repo.client.set(
                                    done_key, 1, ex=_IDEMPOTENCY_DONE_TTL_SECONDS
                                )
                        else:
                            redis_repo.client.set(
                                done_key, 1, ex=_IDEMPOTENCY_DONE_TTL_SECONDS
                            )

                        return Response(status_code=200)

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
                    ),
                )

                # Cache reply antes do envio, para suportar retries do provedor.
                redis_repo.client.set(
                    reply_key,
                    _serialize_twilio_outbound(response_dto),
                    ex=_IDEMPOTENCY_REPLY_TTL_SECONDS,
                )

                message_type = getattr(response_dto, "message_type", "text") or "text"
                media_ids = getattr(response_dto, "media_ids", []) or []
                media_caption = getattr(response_dto, "media_caption", None)

                result = {"success": False}
                if message_type in ("photo", "photo_set") and media_ids:
                    if message_type == "photo":
                        media_id = media_ids[0]
                        url = f"{public_media_base_url.rstrip('/')}/saas/hotel/{hotel_id}/media-public/{media_id}"
                        caption = media_caption if media_caption is not None else (response_dto.reply or "")
                        result = whatsapp_twilio_client.send_media_message(
                            from_phone,
                            message=caption,
                            media_url=url,
                        )
                    else:
                        last_send = {"success": False}
                        for media_id in media_ids[:3]:
                            url = f"{public_media_base_url.rstrip('/')}/saas/hotel/{hotel_id}/media-public/{media_id}"
                            last_send = whatsapp_twilio_client.send_media_message(
                                from_phone,
                                message=media_caption or "",
                                media_url=url,
                            )
                        result = last_send

                    # Para photo_set enviamos também o texto perguntando preferência.
                    if response_dto.reply:
                        text_res = whatsapp_twilio_client.send_text_message(
                            from_phone, response_dto.reply
                        )
                        if not text_res.get("success"):
                            result = text_res
                else:
                    result = whatsapp_twilio_client.send_text_message(from_phone, response_dto.reply)
                elapsed_ms = int((time.perf_counter() - started_at) * 1000)

                if result.get("success"):
                    logger.info(f"✅ [TWILIO] Resposta enviada para {from_phone}")
                    redis_repo.client.set(done_key, 1, ex=_IDEMPOTENCY_DONE_TTL_SECONDS)
                    redis_repo.client.delete(reply_key)
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

                return Response(status_code=200)
            except Exception as e:
                logger.error(f"❌ Erro processando mensagem Twilio (idempotente): {str(e)}", exc_info=True)
                return Response(status_code=200)
            finally:
                _release_redis_lock(redis_repo, lock_key, token)

        # Sem message_sid (improvável), processa sem deduplicação.
        _track_saas(
            phone=from_phone,
            source="twilio",
            event_type="inbound_message",
            details={"message_sid": message_sid},
            hotel_id=hotel_id,
        )

        out_of_hours_reply = _get_out_of_hours_reply_text(hotel_id)
        if out_of_hours_reply:
            started_at = time.perf_counter()
            result = whatsapp_twilio_client.send_text_message(from_phone, out_of_hours_reply)
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)

            _track_saas(
                phone=from_phone,
                source="twilio",
                event_type="outbound_message",
                success=bool(result.get("success")),
                response_time_ms=elapsed_ms,
                details={"message_sid": message_sid, "out_of_hours": True},
                hotel_id=hotel_id,
            )
            return Response(status_code=200)

        debounce_seconds = _get_whatsapp_rate_limit_debounce_seconds(hotel_id)
        if debounce_seconds and debounce_seconds > 0:
            redis_repo = RedisRepository()
            now_ts = time.time()
            rate_last_key = f"whatsapp:rate_limit:last:{hotel_id or 'unknown'}:{from_phone}"
            last_ts_raw = redis_repo.client.get(rate_last_key)
            last_ts = None
            if last_ts_raw:
                try:
                    last_ts = float(last_ts_raw)
                except (TypeError, ValueError):
                    last_ts = None

            redis_repo.client.set(rate_last_key, str(now_ts), ex=int(debounce_seconds) + 30)
            if last_ts is not None and now_ts - last_ts < debounce_seconds:
                warn_key = f"whatsapp:rate_limit:warned:{hotel_id or 'unknown'}:{from_phone}"
                should_warn = not bool(redis_repo.client.exists(warn_key))
                if should_warn:
                    redis_repo.client.set(warn_key, 1, ex=int(debounce_seconds) + 10)
                    warn_text = (
                        "Estou processando sua solicitação. "
                        "Por favor, aguarde alguns segundos e tente novamente."
                    )
                    whatsapp_twilio_client.send_text_message(from_phone, warn_text)
                return Response(status_code=200)

        has_media = num_media > 0
        started_at = time.perf_counter()
        response_dto = use_case.execute(
            hotel_id=hotel_id,
            request_dto=WhatsAppMessageRequestDTO(
                phone=from_phone,
                message=message_body,
                source="twilio",
                has_media=has_media,
            ),
        )

        message_type = getattr(response_dto, "message_type", "text") or "text"
        media_ids = getattr(response_dto, "media_ids", []) or []
        media_caption = getattr(response_dto, "media_caption", None)

        result = {"success": False}
        if message_type in ("photo", "photo_set") and media_ids:
            if message_type == "photo":
                media_id = media_ids[0]
                url = f"{public_media_base_url.rstrip('/')}/saas/hotel/{hotel_id}/media-public/{media_id}"
                caption = media_caption if media_caption is not None else (response_dto.reply or "")
                result = whatsapp_twilio_client.send_media_message(
                    from_phone,
                    message=caption,
                    media_url=url,
                )
            else:
                last_send = {"success": False}
                for media_id in media_ids[:3]:
                    url = f"{public_media_base_url.rstrip('/')}/saas/hotel/{hotel_id}/media-public/{media_id}"
                    last_send = whatsapp_twilio_client.send_media_message(
                        from_phone,
                        message=media_caption or "",
                        media_url=url,
                    )
                result = last_send

            if response_dto.reply:
                text_res = whatsapp_twilio_client.send_text_message(from_phone, response_dto.reply)
                result = text_res if not text_res.get("success") else result
        else:
            result = whatsapp_twilio_client.send_text_message(from_phone, response_dto.reply)
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)

        _track_saas(
            phone=from_phone,
            source="twilio",
            event_type="outbound_message",
            success=bool(result.get("success")),
            response_time_ms=elapsed_ms,
            details={"message_sid": message_sid},
            hotel_id=hotel_id,
        )

        return Response(status_code=200)
    
    except Exception as e:
        logger.error(f"❌ Erro processando webhook Twilio: {str(e)}", exc_info=True)
        return Response(status_code=200)


# ==================== MESSAGE HANDLERS ====================
async def _handle_incoming_message(
    message: dict,
    use_case: HandleWhatsAppMessageUseCase,
    hotel_id: str | None,
    public_media_base_url: str,
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
    
    original_message_id = message.get("id") or message.get("wamid")
    message_id = original_message_id or ""
    from_phone = _normalize_phone(message.get("from"))
    timestamp = message.get("timestamp")
    msg_type = message.get("type")
    
    logger.info(f"📱 Mensagem de {from_phone} | tipo: {msg_type} | id: {message_id}")

    if not hotel_id:
        logger.warning(
            f"⚠️ [META] hotel_id não resolvido para mensagem {message_id} (to_phone_id desconhecido). Ignorando processamento para evitar namespaces 'None'."
        )
        return Response(status_code=200)

    # Robustez do webhook: idempotência + lock.
    # Em alguns payloads Meta, o `message.id` pode vir vazio; ainda assim queremos
    # deduplicar para evitar reenvios (ex: mensagens duplicadas de botões).
    source = "meta"
    should_mark_as_read = bool(original_message_id)
    if not message_id:
        import hashlib

        content_for_key = _extract_message_content(message, msg_type) or ""
        content_hash = hashlib.md5(content_for_key.encode("utf-8")).hexdigest()  # nosec
        message_id = (
            f"surrogate:{from_phone}:{msg_type}:{timestamp}:{content_hash}"
        )

    redis_repo = RedisRepository()
    done_key = _idempotency_done_key(hotel_id, source, message_id)
    reply_key = _idempotency_reply_key(hotel_id, source, message_id)
    lock_key = _idempotency_lock_key(hotel_id, source, message_id)

    # Se já foi processado com sucesso, ignore o replay do provedor.
    if redis_repo.client.exists(done_key):
        logger.info(f"🔁 [META] Ignorando duplicado (done): {message_id}")
        return

    token = _acquire_redis_lock(redis_repo, lock_key)
    if not token:
        logger.info(f"⏳ [META] Ignorando duplicado (lock): {message_id}")
        return

    try:
        # Se uma tentativa anterior calculou a resposta mas falhou ao enviar,
        # reaproveite a resposta para não reexecutar efeitos colaterais.
        cached_reply = redis_repo.client.get(reply_key)
        if cached_reply:
            reply_text = (
                cached_reply.decode("utf-8")
                if isinstance(cached_reply, (bytes, bytearray))
                else str(cached_reply)
            )
            started_at = time.perf_counter()
            cached_payload = _try_deserialize_meta_cached_reply(reply_text)
            if cached_payload:
                message_type = cached_payload.get("message_type")
                if message_type == "button":
                    result = whatsapp_client.send_button_message(
                        from_phone,
                        cached_payload.get("reply", ""),
                        cached_payload.get("buttons", []) or [],
                    )
                elif message_type == "list":
                    result = whatsapp_client.send_list_message(
                        from_phone,
                        header=cached_payload.get("list_header", "") or "",
                        body=cached_payload.get("list_body", None) or cached_payload.get("reply", ""),
                        items=cached_payload.get("list_items", []) or [],
                    )
                elif message_type == "photo":
                    media_ids = cached_payload.get("media_ids", []) or []
                    if media_ids:
                        media_id = media_ids[0]
                        url = f"{public_media_base_url.rstrip('/')}/saas/hotel/{hotel_id}/media-public/{media_id}"
                        caption = cached_payload.get("media_caption") or cached_payload.get("reply") or ""
                        result = whatsapp_client.send_image_message(from_phone, caption, url)
                    else:
                        result = whatsapp_client.send_text_message(from_phone, cached_payload.get("reply", "") or "")
                elif message_type == "photo_set":
                    media_ids = cached_payload.get("media_ids", []) or []
                    caption = cached_payload.get("media_caption") or ""
                    last_result: dict = {"success": False}
                    all_success = True
                    for media_id in media_ids[:3]:
                        url = f"{public_media_base_url.rstrip('/')}/saas/hotel/{hotel_id}/media-public/{media_id}"
                        last_result = whatsapp_client.send_image_message(from_phone, caption, url)
                        all_success = all_success and bool(last_result.get("success"))

                    if not all_success:
                        result = last_result
                    else:
                        buttons = cached_payload.get("buttons", []) or []
                        pref_reply = cached_payload.get("reply", "") or "Qual prefere? (1/2/3)"
                        if buttons:
                            result = whatsapp_client.send_button_message(
                                from_phone,
                                pref_reply,
                                buttons,
                            )
                        elif pref_reply:
                            result = whatsapp_client.send_text_message(from_phone, pref_reply)
                        else:
                            result = last_result
                else:
                    result = whatsapp_client.send_text_message(
                        from_phone, cached_payload.get("reply", "") or ""
                    )
            else:
                result = whatsapp_client.send_text_message(from_phone, reply_text)
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)

            _track_saas(
                phone=from_phone,
                source="meta",
                event_type="outbound_message",
                success=bool(result.get("success")),
                response_time_ms=elapsed_ms,
                details={"message_id": message_id, "type": msg_type},
                hotel_id=hotel_id,
            )

            if result.get("success"):
                redis_repo.client.set(done_key, 1, ex=_IDEMPOTENCY_DONE_TTL_SECONDS)
                redis_repo.client.delete(reply_key)
            return

        # Marca como lida (double blue check)
        if should_mark_as_read:
            whatsapp_client.mark_as_read(message_id)

        # Extrai conteúdo baseado no tipo
        content = _extract_message_content(message, msg_type)
        has_media = msg_type in ("image", "document", "audio", "video")

        logger.info(f"📝 Conteúdo: '{content}' | has_media: {has_media}")

        _track_saas(
            phone=from_phone,
            source="meta",
            event_type="inbound_message",
            details={"message_id": message_id, "type": msg_type},
            hotel_id=hotel_id,
        )

        debounce_seconds = _get_whatsapp_rate_limit_debounce_seconds(hotel_id)
        if debounce_seconds and debounce_seconds > 0:
            now_ts = time.time()
            rate_last_key = f"whatsapp:rate_limit:last:{hotel_id or 'unknown'}:{from_phone}"
            last_ts_raw = redis_repo.client.get(rate_last_key)
            last_ts = None
            if last_ts_raw:
                try:
                    last_ts = float(last_ts_raw)
                except (TypeError, ValueError):
                    last_ts = None

            # Atualiza timestamp mesmo se rate limited para manter debounce.
            redis_repo.client.set(rate_last_key, str(now_ts), ex=int(debounce_seconds) + 30)

            if last_ts is not None and now_ts - last_ts < debounce_seconds:
                warn_key = f"whatsapp:rate_limit:warned:{hotel_id or 'unknown'}:{from_phone}"
                should_warn = not bool(redis_repo.client.exists(warn_key))
                if should_warn:
                    redis_repo.client.set(warn_key, 1, ex=int(debounce_seconds) + 10)
                    warn_text = (
                        "Estou processando sua solicitação. "
                        "Por favor, aguarde alguns segundos e tente novamente."
                    )
                    started_at = time.perf_counter()
                    result = whatsapp_client.send_text_message(from_phone, warn_text)
                    elapsed_ms = int((time.perf_counter() - started_at) * 1000)

                    _track_saas(
                        phone=from_phone,
                        source="meta",
                        event_type="outbound_message",
                        success=bool(result.get("success")),
                        response_time_ms=elapsed_ms,
                        details={
                            "message_id": message_id,
                            "type": msg_type,
                            "rate_limited": True,
                        },
                        hotel_id=hotel_id,
                    )

                    if result.get("success"):
                        redis_repo.client.set(
                            done_key, 1, ex=_IDEMPOTENCY_DONE_TTL_SECONDS
                        )
                    return

                # Rate limited silencioso: apenas marca como processado.
                redis_repo.client.set(done_key, 1, ex=_IDEMPOTENCY_DONE_TTL_SECONDS)
                return

        out_of_hours_reply = _get_out_of_hours_reply_text(hotel_id)
        if out_of_hours_reply:
            started_at = time.perf_counter()
            redis_repo.client.set(reply_key, out_of_hours_reply, ex=_IDEMPOTENCY_REPLY_TTL_SECONDS)
            result = whatsapp_client.send_text_message(from_phone, out_of_hours_reply)
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)

            if result.get("success"):
                logger.info(f"⏸️ Resposta fora do atendimento enviada para {from_phone}")
                redis_repo.client.set(done_key, 1, ex=_IDEMPOTENCY_DONE_TTL_SECONDS)
                redis_repo.client.delete(reply_key)
            else:
                logger.error(
                    f"❌ Erro ao enviar resposta fora do atendimento: {result.get('error')}"
                )

            _track_saas(
                phone=from_phone,
                source="meta",
                event_type="outbound_message",
                success=bool(result.get("success")),
                response_time_ms=elapsed_ms,
                details={"message_id": message_id, "type": msg_type, "out_of_hours": True},
                hotel_id=hotel_id,
            )
            return

        started_at = time.perf_counter()
        response_dto = use_case.execute(
            hotel_id=hotel_id,
            request_dto=WhatsAppMessageRequestDTO(
                phone=from_phone,
                message=content,
                source="meta",
                has_media=has_media,
            ),
        )

        # Cache reply antes do envio, para suportar retries do provedor.
        redis_repo.client.set(
            reply_key,
            _serialize_meta_outbound(response_dto),
            ex=_IDEMPOTENCY_REPLY_TTL_SECONDS,
        )

        result = _send_meta_outbound(
            whatsapp_client,
            from_phone,
            response_dto,
            public_media_base_url=public_media_base_url,
            hotel_id=hotel_id,
        )
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)

        if result.get("success"):
            logger.info(f"✅ Resposta enviada para {from_phone}")
            redis_repo.client.set(done_key, 1, ex=_IDEMPOTENCY_DONE_TTL_SECONDS)
            redis_repo.client.delete(reply_key)
        else:
            logger.error(f"❌ Erro ao enviar resposta: {result.get('error')}")

        _track_saas(
            phone=from_phone,
            source="meta",
            event_type="outbound_message",
            success=bool(result.get("success")),
            response_time_ms=elapsed_ms,
            details={"message_id": message_id, "type": msg_type},
            hotel_id=hotel_id,
        )
    except Exception as e:
        logger.error(f"❌ Erro ao processar mensagem: {str(e)}", exc_info=True)
        # Notifica erro ao usuário (não marca done para permitir retry)
        try:
            whatsapp_client.send_text_message(
                from_phone,
                "Desculpa, ocorreu um erro. Tente novamente mais tarde.",
            )
        except Exception:
            pass
    finally:
        _release_redis_lock(redis_repo, lock_key, token)


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
            # Preferimos o `id` para manter o parsing estável.
            # Mas, para UX do fluxo de fotos, se o `title` contiver palavras
            # como "foto/fotos/imagem", usamos o `title` para não perder a intenção.
            btn_id = button_reply.get("id")
            btn_title = (button_reply.get("title") or "").strip()
            title_lower = btn_title.lower()
            photo_related = any(
                kw in title_lower for kw in ["foto", "fotos", "imagem", "imagens"]
            )
            if photo_related and btn_title:
                return btn_title
            return btn_id or btn_title
        
        # Resposta de lista
        list_reply = interactive.get("list_reply", {})
        if list_reply:
            list_id = list_reply.get("id")
            list_title = (list_reply.get("title") or "").strip()
            title_lower = list_title.lower()
            photo_related = any(
                kw in title_lower for kw in ["foto", "fotos", "imagem", "imagens"]
            )
            if photo_related and list_title:
                return list_title
            return list_id or list_title
        
        return "[interactive]"
    
    elif msg_type in ("image", "document", "audio", "video"):
        media = message.get(msg_type, {}) or {}
        caption = media.get("caption") or ""

        metadata_parts: list[str] = []
        # Metadados "textuais" que ajudam a entender a intenção do usuário.
        if msg_type == "document":
            filename = media.get("filename") or media.get("file_name")
            if filename:
                metadata_parts.append(f"arquivo: {filename}")

        title = media.get("title")
        if title:
            metadata_parts.append(f"título: {title}")

        mime_type = media.get("mime_type")
        if mime_type:
            metadata_parts.append(f"tipo: {mime_type}")

        media_id = media.get("id") or media.get("media_id")
        if media_id:
            metadata_parts.append(f"id: {media_id}")

        metadata_text = ", ".join(metadata_parts)
        if caption:
            if metadata_text:
                return f"{caption}\n{metadata_text}"
            return caption

        if metadata_text:
            return metadata_text

        return f"[{msg_type.upper()}]"
    
    else:
        # Para outros tipos (imagem, arquivo, etc)
        return f"[{msg_type.upper()}]"


def _handle_message_status(status: dict, hotel_id: str | None):
    """
    Processa status de entrega de mensagem.
    
    Tipos: "sent", "delivered", "read", "failed"
    """
    
    status_id = status.get("id")
    status_type = status.get("status")
    recipient = status.get("recipient_id")
    timestamp = status.get("timestamp")
    should_process = True
    redis_repo = RedisRepository()

    if status_id:
        done_key = f"whatsapp:status:done:{hotel_id or 'unknown'}:{status_id}"
        try:
            if redis_repo.client.exists(done_key):
                return
            should_process = True
            # Marca como processado antes de logar
            redis_repo.client.set(done_key, 1, ex=_IDEMPOTENCY_DONE_TTL_SECONDS)
        except Exception:
            # Se Redis falhar, não impede rastreio/log
            pass
    else:
        # Sem status_id não temos deduplicação; ainda assim registramos logs.
        should_process = True

    logger.info(
        f"📊 Status: {status_id} → {status_type} (destinatário: {recipient})"
    )
    
    if (
        should_process
        and status_type == "failed"
        and whatsapp_client
        and recipient
    ):
        try:
            recipient_phone = _normalize_phone(str(recipient))
            if recipient_phone:
                failed_key = f"whatsapp:delivery:failed:notified:{hotel_id or 'unknown'}:{recipient_phone}:{status_id or 'unknown'}"
                # evita avisos duplicados em falhas em cascata
                if not redis_repo.client.exists(failed_key):
                    redis_repo.client.set(
                        failed_key,
                        1,
                        ex=_IDEMPOTENCY_DONE_TTL_SECONDS,
                    )

                    whatsapp_client.send_text_message(
                        recipient_phone,
                        "Desculpe, não consegui enviar sua mensagem. Tente novamente em alguns instantes.",
                    )
        except Exception:
            pass

    # Você pode guardar isso no banco para rastreamento
    # Exemplo: logs_db.insert({"message_id": message_id, "status": status_type, "recipient": recipient})