"""
Handle WhatsApp Message Use-Case - orchestrates inbound message processing.

This use-case keeps the interface layer thin by centralizing decision logic.
"""
import re
import time
import uuid
from datetime import date

from app.domain.entities.payment.payment import Payment

from app.application.dto.cancel_reservation_request_dto import CancelReservationRequestDTO
from app.application.dto.create_reservation_request_dto import CreateReservationRequestDTO
from app.application.dto.checkin_request_dto import CheckinRequestDTO
from app.application.dto.checkout_request_dto import CheckoutRequestDTO
from app.application.dto.confirm_reservation_request_dto import ConfirmReservationRequestDTO
from app.application.dto.extend_reservation_request_dto import ExtendReservationRequestDTO
from app.application.dto.whatsapp_message_request_dto import WhatsAppMessageRequestDTO
from app.application.dto.whatsapp_message_response_dto import WhatsAppMessageResponseDTO
from app.application.use_cases.cancel_reservation import CancelReservationUseCase
from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
from app.application.use_cases.create_reservation import CreateReservationUseCase
from app.application.use_cases.checkout_via_whatsapp import CheckoutViaWhatsAppUseCase
from app.application.use_cases.confirm_reservation import ConfirmReservationUseCase
from app.application.use_cases.conversation import ConversationUseCase
from app.application.use_cases.extend_reservation import ExtendReservationUseCase
from app.domain.repositories.cache_repository import CacheRepository
from app.domain.repositories.hotel_media_repository import HotelMediaRepository
from app.domain.repositories.hotel_repository import HotelRepository
from app.domain.repositories.payment_repository import PaymentRepository
from app.domain.repositories.reservation_repository import ReservationRepository
from app.domain.services.payment_provider import PaymentProvider
from app.domain.entities.reservation.stay_period import StayPeriod
from app.domain.repositories.room_repository import RoomRepository
from app.domain import exceptions


class HandleWhatsAppMessageUseCase:
    """Orchestrates inbound WhatsApp messages and returns a reply."""

    FLOW_KEY_PREFIX = "flow:"
    CONFIRM_RESERVATION_ACTION = "confirm_reservation"
    CANCEL_RESERVATION_ACTION = "cancel_reservation"
    CREATE_RESERVATION_ACTION = "create_reservation"
    EXTEND_RESERVATION_ACTION = "extend_reservation"

    # Flow steps
    STEP_SUMMARY_DISPLAYED = "summary_displayed"
    STEP_AWAITING_CONFIRMATION = "awaiting_confirmation"
    STEP_AWAITING_EDIT_CHOICE = "awaiting_edit_choice"
    STEP_AWAITING_ROOM_SELECTION = "awaiting_room_selection"
    STEP_AWAITING_NEW_DATES = "awaiting_new_dates"
    STEP_AWAITING_DATES = "awaiting_dates"
    STEP_AWAITING_ROOM_CHOICE = "awaiting_room_choice"
    STEP_AWAITING_NAME = "awaiting_name"
    STEP_AWAITING_GUEST_COUNT = "awaiting_guest_count"
    STEP_AWAITING_CHILDREN = "awaiting_children"
    STEP_AWAITING_CHILDREN_COUNT = "awaiting_children_count"
    STEP_AWAITING_CREATE_CONFIRMATION = "awaiting_create_confirmation"
    STEP_AWAITING_PAYMENT_CHOICE = "awaiting_payment_choice"
    STEP_AWAITING_PAYMENT_PROOF = "awaiting_payment_proof"
    STEP_AWAITING_NEW_CHECKOUT = "awaiting_new_checkout"
    PRE_CHECKIN_ACTION = "pre_checkin"
    STEP_AWAITING_DOCUMENT = "awaiting_document"
    STEP_AWAITING_ARRIVAL_TIME = "awaiting_arrival_time"

    PHOTO_REQUEST_ACTION = "photo_request"
    STEP_AWAITING_PHOTO_CHOICE = "awaiting_photo_choice"

    # 6.3 Fallback humano
    FALLBACK_HUMAN_MESSAGE = (
        "Se precisar de atendimento humano, digite ATENDENTE ou ligue para o hotel."
    )

    # Instruções de pagamento (Fase 0 - manual). Configurável via PAYMENT_INSTRUCTIONS.
    DEFAULT_PAYMENT_INSTRUCTIONS_TEMPLATE = (
        "💳 Pagamento via PIX ou transferência.\n"
        "Chave PIX: {pix_key}\n"
        "Envie o comprovante para confirmarmos sua reserva."
    )

    def __init__(
        self,
        checkin_use_case: CheckInViaWhatsAppUseCase,
        checkout_use_case: CheckoutViaWhatsAppUseCase,
        cancel_reservation_use_case: CancelReservationUseCase,
        create_reservation_use_case: CreateReservationUseCase,
        conversation_use_case: ConversationUseCase,
        confirm_reservation_use_case: ConfirmReservationUseCase,
        extend_reservation_use_case: ExtendReservationUseCase,
        reservation_repository: ReservationRepository,
        cache_repository: CacheRepository,
        room_repository: RoomRepository,
        hotel_repository: HotelRepository,
        payment_provider: PaymentProvider,
        payment_repository: PaymentRepository,
        pre_checkin_use_case=None,
        support_ticket_use_case=None,
        room_order_use_case=None,
        hotel_media_repository: HotelMediaRepository | None = None,
    ):
        self.checkin_use_case = checkin_use_case
        self.checkout_use_case = checkout_use_case
        self.cancel_reservation_use_case = cancel_reservation_use_case
        self.create_reservation_use_case = create_reservation_use_case
        self.conversation_use_case = conversation_use_case
        self.confirm_reservation_use_case = confirm_reservation_use_case
        self.extend_reservation_use_case = extend_reservation_use_case
        self.reservation_repository = reservation_repository
        self.cache_repository = cache_repository
        self.room_repository = room_repository
        self.hotel_repository = hotel_repository
        self.payment_provider = payment_provider
        self.payment_repository = payment_repository
        self.pre_checkin_use_case = pre_checkin_use_case
        self.support_ticket_use_case = support_ticket_use_case
        self.room_order_use_case = room_order_use_case
        self.hotel_media_repository = hotel_media_repository

    def execute(self, hotel_id: str, request_dto: WhatsAppMessageRequestDTO) -> WhatsAppMessageResponseDTO:
        text = (request_dto.message or "").strip()
        content_lower = text.lower()
        phone = request_dto.phone

        flow_state = self._get_flow_state(f"{hotel_id}:{phone}")

        # Recovery de contexto: quando o fluxo expirou ou o estado retornou inconsistente,
        # evita cair em fallback/intenções aleatórias.
        if not flow_state and self._looks_like_flow_continuation(content_lower):
            return self._context_lost_response(hotel_id, phone)

        known_actions = {
            self.CREATE_RESERVATION_ACTION,
            self.CANCEL_RESERVATION_ACTION,
            self.CONFIRM_RESERVATION_ACTION,
            self.EXTEND_RESERVATION_ACTION,
            self.PRE_CHECKIN_ACTION,
            self.PHOTO_REQUEST_ACTION,
        }
        if flow_state and flow_state.get("action") not in known_actions:
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return self._context_lost_response(hotel_id, phone)

        # Prioridade UX: se o usuário pedir fotos, tratamos pelo fluxo de fotos,
        # mesmo que ele esteja em outro fluxo (ex: pagamento/confirmação).
        if self._is_photo_request_intent(content_lower) and not (
            flow_state and flow_state.get("action") == self.PHOTO_REQUEST_ACTION
        ):
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return self._handle_new_photo_request(hotel_id, phone, content_lower)
        
        # Handle ongoing flows
        has_media = getattr(request_dto, "has_media", False)
        if flow_state and flow_state.get("action") == self.CREATE_RESERVATION_ACTION:
            return self._handle_create_reservation_flow(
                hotel_id, phone, text, content_lower, flow_state, has_media=has_media
            )

        if flow_state and flow_state.get("action") == self.CANCEL_RESERVATION_ACTION:
            return self._handle_cancel_reservation_flow(hotel_id, phone, content_lower, flow_state)

        if flow_state and flow_state.get("action") == self.CONFIRM_RESERVATION_ACTION:
            return self._handle_confirm_reservation_flow(hotel_id, phone, text, content_lower, flow_state)

        if flow_state and flow_state.get("action") == self.EXTEND_RESERVATION_ACTION:
            return self._handle_extend_reservation_flow(hotel_id, phone, text, content_lower, flow_state)

        if flow_state and flow_state.get("action") == self.PRE_CHECKIN_ACTION:
            return self._handle_pre_checkin_flow(hotel_id, phone, text, content_lower, flow_state)

        if flow_state and flow_state.get("action") == self.PHOTO_REQUEST_ACTION:
            return self._handle_photo_request_flow(hotel_id, phone, content_lower, flow_state)

        # Pix proof pode chegar quando o fluxo foi finalizado/limpo (ex: cartão disponível).
        # Se não há flow_state e chegou mídia, tentamos tratar como comprovante para reserva PENDING.
        if (not flow_state) and has_media:
            direct_proof_resp = self._try_handle_payment_proof_without_flow_state(
                hotel_id=hotel_id,
                phone=phone,
            )
            if direct_proof_resp:
                return direct_proof_resp

        # Saudações iniciais: primeira mensagem deve ser acolhedora e personalizada
        # com o nome do hotel, evitando respostas "padronizadas" genéricas.
        if (not flow_state) and self._is_greeting_message(content_lower):
            if not self._has_conversation_history(hotel_id, phone):
                hotel = self.hotel_repository.get_active_hotel(hotel_id)
                hotel_name = (getattr(hotel, "name", None) or "seu hotel").strip()
                # Evita duplicar "Hotel" quando o nome já vem como "Hotel X".
                if hotel_name.lower().startswith("hotel "):
                    hotel_label = hotel_name
                else:
                    hotel_label = f"Hotel {hotel_name}"
                greeting = self._format_welcome_greeting(content_lower)
                return WhatsAppMessageResponseDTO(
                    reply=f"{greeting}, seja bem-vindo(a) ao {hotel_label}.\n\nComo posso ajudar?",
                    success=True,
                )

        # 6.3 Fallback humano explícito
        if "atendente" in content_lower and len(content_lower.strip()) < 15:
            return WhatsAppMessageResponseDTO(
                reply=(
                    "📞 Transferindo para atendimento humano.\n\n"
                    "Nossa equipe entrará em contato em breve. "
                    "Ou ligue diretamente para a recepção."
                ),
                success=True,
            )

        # Check for new flow intentions
        if self._is_create_reservation_intent(content_lower):
            return self._start_create_reservation_flow(hotel_id, phone)

        if self._is_cancel_reservation_intent(content_lower):
            return self._start_cancel_reservation_flow(hotel_id, phone)

        if self._is_confirm_reservation_intent(content_lower):
            return self._start_confirm_reservation_flow(hotel_id, phone)

        if self._is_extend_reservation_intent(content_lower):
            return self._start_extend_reservation_flow(hotel_id, phone)

        # 6.4 Chave digital - hóspede checked-in pede código
        if ("chave" in content_lower or "código" in content_lower or "codigo" in content_lower):
            reservation = self.reservation_repository.find_by_phone_number(phone, hotel_id)
            if reservation and reservation.status.name == "CHECKED_IN" and getattr(reservation, "digital_key_code", None):
                return WhatsAppMessageResponseDTO(
                    reply=f"🔑 Seu código de acesso: {reservation.digital_key_code}\n\nUse na fechadura do quarto.",
                    success=True,
                )

        if "check-in" in content_lower or "checkin" in content_lower:
            try:
                response_dto = self.checkin_use_case.execute(
                    hotel_id, CheckinRequestDTO(phone=phone)
                )
                return WhatsAppMessageResponseDTO(
                    reply=response_dto.message,
                    success=response_dto.success,
                    error=response_dto.error,
                )
            except Exception as exc:
                return WhatsAppMessageResponseDTO(
                    reply=f"Erro ao processar check-in: {exc}",
                    success=False,
                    error=str(exc),
                )

        if self._is_checkout_intent(content_lower):
            try:
                response_dto = self.checkout_use_case.execute(
                    hotel_id, CheckoutRequestDTO(phone=phone)
                )
                return WhatsAppMessageResponseDTO(
                    reply=response_dto.message,
                    success=response_dto.success,
                    error=response_dto.error,
                )
            except Exception as exc:
                return WhatsAppMessageResponseDTO(
                    reply=f"Erro ao processar check-out: {exc}",
                    success=False,
                    error=str(exc),
                )

        # 6.1 Pré-check-in
        if self.pre_checkin_use_case and self._is_pre_checkin_intent(content_lower):
            return self._start_pre_checkin_flow(hotel_id, phone)

        # 6.6 Resolução de problemas - reportar problema
        if self.support_ticket_use_case and self._is_support_ticket_intent(content_lower):
            return self._handle_support_ticket(phone, text)

        # 6.5 Pedidos durante estadia
        if self.room_order_use_case and self._is_room_order_intent(content_lower):
            return self._handle_room_order(phone, content_lower)

        # Fotos (hotel geral ou por quarto)
        if self._is_photo_request_intent(content_lower):
            return self._handle_new_photo_request(hotel_id, phone, content_lower)

        # Pergunta direta: "de que hotel estou falando?"
        if self._is_hotel_identity_question(content_lower):
            try:
                hotel = self.hotel_repository.get_active_hotel(hotel_id)
                if hotel:
                    reply = f"Você está falando com o hotel {getattr(hotel, 'name', 'seu hotel')}."
                    contact_phone = getattr(hotel, "contact_phone", None)
                    if contact_phone:
                        reply += f"\nContato do hotel: {contact_phone}"
                else:
                    reply = "Não consegui identificar o hotel para sua conversa."

                if self._should_offer_human_message(content_lower) and self.FALLBACK_HUMAN_MESSAGE:
                    reply = f"{reply}\n\n{self.FALLBACK_HUMAN_MESSAGE}"

                return WhatsAppMessageResponseDTO(reply=reply, success=True)
            except Exception:
                # Não quebra o fluxo: cai no fallback padrão do sistema.
                pass

        if "reserva" in content_lower or "booking" in content_lower:
            try:
                ai_reply = self.conversation_use_case.execute(hotel_id, phone, text)
                return WhatsAppMessageResponseDTO(reply=ai_reply, success=True)
            except Exception as exc:
                return WhatsAppMessageResponseDTO(
                    reply="Para fazer uma reserva, envie: RESERVA",
                    success=False,
                    error=str(exc),
                )

        try:
            ai_reply = self.conversation_use_case.execute(hotel_id, phone, text)
            reply = ai_reply
            if (
                self._should_offer_human_message(content_lower)
                and self.FALLBACK_HUMAN_MESSAGE
                and reply
            ):
                reply = f"{reply}\n\n{self.FALLBACK_HUMAN_MESSAGE}"
            return WhatsAppMessageResponseDTO(reply=reply or ai_reply, success=True)
        except Exception as exc:
            return WhatsAppMessageResponseDTO(
                reply=(
                    f"Recebi sua mensagem: '{text}'\n\n"
                    "Como posso ajudar? Você pode fazer reserva, check-in, checkout ou cancelar.\n\n"
                    f"{self.FALLBACK_HUMAN_MESSAGE if self._should_offer_human_message(content_lower) else ''}"
                ),
                success=False,
                error=str(exc),
            )

    @staticmethod
    def _is_photo_request_intent(content_lower: str) -> bool:
        if not content_lower:
            return False
        return any(
            kw in content_lower
            for kw in [
                "foto",
                "fotos",
                "imagem",
                "imagens",
                "me mostra",
                "quero ver",
                "mostra",
            ]
        )

    @staticmethod
    def _extract_room_number_from_text(content_lower: str) -> str | None:
        """
        Tenta extrair número de quarto quando o usuário manda algo como:
        "quarto 101" / "quarto 1" / "room 12"
        """
        if not content_lower:
            return None

        m = re.search(r"(?:quarto|room)\s*(\d{1,4})\b", content_lower)
        if m:
            return m.group(1)

        # fallback: se a mensagem for apenas dígitos (ex: "101"), tratamos como tentativa de quarto
        stripped = content_lower.strip()
        if re.fullmatch(r"\d{1,4}", stripped):
            return stripped
        return None

    def _get_photo_scope_and_room_number(
        self,
        hotel_id: str,
        phone: str,
        content_lower: str,
    ) -> tuple[str, str | None]:
        # Heurística de escopo:
        # - se o texto menciona "quarto" e conseguimos inferir o número, usamos ROOM
        # - se menciona "quarto" mas não dá para inferir, voltamos para HOTEL (melhora UX)
        room_keywords = ["quarto", "cama", "suite", "acomodacao", "acomodação", "room"]
        mentions_room = any(kw in content_lower for kw in room_keywords)

        if not mentions_room:
            return "HOTEL", None

        # mentions_room == True -> tenta inferir número
        room_number: str | None = None
        try:
            reservation = self.reservation_repository.find_by_phone_number(phone, hotel_id)
            room_number = getattr(reservation, "room_number", None)
        except Exception:
            room_number = None

        if not room_number:
            room_number = self._extract_room_number_from_text(content_lower)

        if room_number:
            return "ROOM", room_number

        # Sem número do quarto: fallback para fotos do hotel geral.
        return "HOTEL", None

    def _handle_new_photo_request(
        self,
        hotel_id: str,
        phone: str,
        content_lower: str,
    ) -> WhatsAppMessageResponseDTO:
        if not self.hotel_media_repository:
            # Fallback: deixa a IA lidar.
            ai_reply = self.conversation_use_case.execute(hotel_id, phone, content_lower)
            return WhatsAppMessageResponseDTO(reply=ai_reply, success=True)

        scope, room_number = self._get_photo_scope_and_room_number(hotel_id, phone, content_lower)

        media_ids = self.hotel_media_repository.get_media_set_photo_ids(
            hotel_id=hotel_id,
            scope=scope,
            room_number=room_number,
            limit=3,
        )

        if not media_ids:
            if scope == "ROOM":
                hint = f"para o quarto {room_number}" if room_number else "por quarto"
                return WhatsAppMessageResponseDTO(
                    reply=f"Desculpe, ainda não tenho fotos cadastradas {hint}.",
                    success=True,
                )
            return WhatsAppMessageResponseDTO(
                reply="Desculpe, ainda não tenho fotos cadastradas do hotel.",
                success=True,
            )

        flow_state = {
            "action": self.PHOTO_REQUEST_ACTION,
            "step": self.STEP_AWAITING_PHOTO_CHOICE,
            "photos": media_ids[:3],
            "scope": scope,
            "room_number": room_number,
        }
        self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)

        buttons_full = [
            {"id": "1", "title": "Foto 1"},
            {"id": "2", "title": "Foto 2"},
            {"id": "3", "title": "Foto 3"},
        ]
        selected_ids = media_ids[:3]
        buttons = buttons_full[: len(selected_ids)]

        return WhatsAppMessageResponseDTO(
            reply="Vou te enviar 3 fotos. Qual prefere? (responda 1, 2 ou 3)",
            success=True,
            message_type="photo_set",
            media_ids=selected_ids,
            media_caption="",
            buttons=buttons,
        )

    def _handle_photo_request_flow(
        self,
        hotel_id: str,
        phone: str,
        content_lower: str,
        flow_state: dict,
    ) -> WhatsAppMessageResponseDTO:
        step = flow_state.get("step", self.STEP_AWAITING_PHOTO_CHOICE)
        if step != self.STEP_AWAITING_PHOTO_CHOICE:
            return self._context_lost_response(hotel_id, phone)

        photos: list[str] = flow_state.get("photos", []) or []
        if not photos:
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return self._context_lost_response(hotel_id, phone)

        stripped = (content_lower or "").strip()
        choice: int | None = None
        if stripped in ("1", "2", "3"):
            choice = int(stripped)
        else:
            m = re.search(r"\b([1-3])\b", content_lower)
            if m:
                choice = int(m.group(1))

        if choice is None or choice < 1 or choice > min(3, len(photos)):
            return WhatsAppMessageResponseDTO(
                reply="Não entendi. Responda 1, 2 ou 3.",
                success=True,
            )

        selected_photo_id = photos[choice - 1]
        self._clear_flow_state(f"{hotel_id}:{phone}")

        return WhatsAppMessageResponseDTO(
            reply="",
            success=True,
            message_type="photo",
            media_ids=[selected_photo_id],
            media_caption=f"Foto {choice}",
        )

    @staticmethod
    def _looks_like_flow_continuation(content_lower: str) -> bool:
        """
        Heurística: se o usuário respondeu algo típico de etapas do fluxo,
        mas não existe flow_state no cache, tratamos como contexto perdido.
        """
        if not content_lower:
            return False

        stripped = content_lower.strip()
        if stripped in ("sim", "s", "nao", "não", "editar", "quarto", "datas"):
            return True
        if re.fullmatch(r"\d", stripped):
            # Respostas de botões de escolha (ex: pagamento e novas perguntas numéricas).
            return True
        return False

    @staticmethod
    def _is_greeting_message(content_lower: str) -> bool:
        if not content_lower:
            return False
        stripped = content_lower.strip()
        greetings = (
            r"^(oi|olá|ola)\b",
            r"^(bom dia)\b",
            r"^(boa tarde)\b",
            r"^(bom tarde)\b",
            r"^(boa noite)\b",
            r"^(bom noite)\b",
            r"^(e aí|e ai|eai)\b",
        )
        return any(re.match(pat, stripped) for pat in greetings)

    @staticmethod
    def _format_welcome_greeting(content_lower: str) -> str:
        if "boa tarde" in content_lower or "bom tarde" in content_lower:
            return "Boa tarde"
        if "boa noite" in content_lower or "bom noite" in content_lower:
            return "Boa noite"
        if "bom dia" in content_lower:
            return "Bom dia"
        return "Olá"

    @staticmethod
    def _should_offer_human_message(content_lower: str) -> bool:
        return any(
            kw in content_lower
            for kw in ["atendente", "atendimento humano", "humano", "falar com"]
        )

    def _has_conversation_history(self, hotel_id: str, phone: str) -> bool:
        try:
            history = self.cache_repository.get(hotel_id, phone)
            return bool(history)
        except Exception:
            # Se a checagem de histórico falhar, não bloqueamos o onboarding.
            return False

    @staticmethod
    def _is_hotel_identity_question(content_lower: str) -> bool:
        if not content_lower:
            return False
        return any(
            kw in content_lower
            for kw in [
                "de que hotel",  # "de que hotel estou falando"
                "qual hotel",
                "estou falando",
                "está falando",
                "nome do hotel",
                "hotel que",
                "que hotel",
            ]
        )

    def _context_lost_response(self, hotel_id: str, phone: str) -> WhatsAppMessageResponseDTO:
        # Garante que o fluxo antigo não atrapalhe reentrada.
        self._clear_flow_state(f"{hotel_id}:{phone}")

        reply = (
            "Perdi seu contexto. Quer fazer:\n"
            "RESERVA / CHECK-IN / CHECKOUT / CANCELAR?\n\n"
            "Escolha uma opção acima (ou digite RESERVA/CHECK-IN/CHECKOUT/CANCELAR)."
        )

        return WhatsAppMessageResponseDTO(
            reply=reply,
            success=True,
            message_type="button",
            buttons=[
                {"id": "reserva", "title": "RESERVA"},
                {"id": "check-in", "title": "CHECK-IN"},
                {"id": "checkout", "title": "CHECKOUT"},
                {"id": "cancelar", "title": "CANCELAR"},
            ],
        )

    def _start_create_reservation_flow(self, hotel_id: str, phone: str) -> WhatsAppMessageResponseDTO:
        """Initiate reservation creation flow."""
        flow_state = {
            "action": self.CREATE_RESERVATION_ACTION,
            "step": self.STEP_AWAITING_DATES,
        }
        self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)
        return WhatsAppMessageResponseDTO(
            reply=(
                "📅 Informe as datas da sua estadia.\n\n"
                "Exemplo: Check-in 15/04/2026 e Check-out 18/04/2026\n"
                "Ou: 15/04/2026 a 18/04/2026"
            ),
            success=True,
        )

    def _handle_create_reservation_flow(
        self,
        hotel_id: str,
        phone: str,
        text: str,
        content_lower: str,
        flow_state: dict,
        has_media: bool = False,
    ) -> WhatsAppMessageResponseDTO:
        """Handle ongoing reservation creation flow."""
        step = flow_state.get("step", self.STEP_AWAITING_DATES)

        # "cancelar" deve cancelar o fluxo em qualquer etapa.
        if "cancelar" in content_lower:
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return WhatsAppMessageResponseDTO(
                reply="❌ Reserva cancelada. Se precisar de algo mais, me avise.",
                success=True,
            )

        # "Não" genérico (nao/não) deve ser interpretado como cancelamento
        # apenas nos passos em que a resposta "SIM/NÃO" significa mesmo abortar.
        if self._is_negative_confirmation(content_lower) and step in (
            self.STEP_AWAITING_PAYMENT_CHOICE,
            self.STEP_AWAITING_PAYMENT_PROOF,
        ):
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return WhatsAppMessageResponseDTO(
                reply="❌ Reserva cancelada. Se precisar de algo mais, me avise.",
                success=True,
            )

        if step == self.STEP_AWAITING_DATES:
            return self._handle_create_awaiting_dates(hotel_id, phone, text, flow_state)

        if step == self.STEP_AWAITING_ROOM_CHOICE:
            return self._handle_create_awaiting_room_choice(hotel_id, phone, content_lower, flow_state)

        if step == self.STEP_AWAITING_NAME:
            return self._handle_create_awaiting_name(hotel_id, phone, text, flow_state)

        if step == self.STEP_AWAITING_GUEST_COUNT:
            return self._handle_create_awaiting_guest_count(
                hotel_id, phone, content_lower, flow_state
            )

        if step == self.STEP_AWAITING_CHILDREN:
            return self._handle_create_awaiting_children(
                hotel_id, phone, content_lower, flow_state
            )

        if step == self.STEP_AWAITING_CHILDREN_COUNT:
            return self._handle_create_awaiting_children_count(
                hotel_id, phone, content_lower, flow_state
            )

        if step == self.STEP_AWAITING_PAYMENT_CHOICE:
            return self._handle_create_awaiting_payment_choice(hotel_id, phone, content_lower, flow_state)

        if step == self.STEP_AWAITING_PAYMENT_PROOF:
            return self._handle_create_awaiting_payment_proof(
                hotel_id, phone, text, flow_state, has_media=has_media
            )

        # Step inconsistente (ex: TTL expirou entre mensagens).
        return self._context_lost_response(hotel_id, phone)

    def _parse_dates_from_text(self, text: str) -> tuple[date | None, date | None]:
        """Extrai duas datas do texto. Retorna (check_in, check_out) ou (None, None)."""
        matches = re.findall(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})", text)
        if len(matches) < 2:
            return None, None

        def to_date(m):
            d, mo, y = int(m[0]), int(m[1]), int(m[2])
            if y < 100:
                y += 2000
            return date(y, mo, d)

        try:
            d1, d2 = to_date(matches[0]), to_date(matches[1])
            if d1 > d2:
                d1, d2 = d2, d1
            return d1, d2
        except (ValueError, IndexError):
            return None, None

    def _handle_create_awaiting_dates(
        self, hotel_id: str, phone: str, text: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Process dates input."""
        check_in, check_out = self._parse_dates_from_text(text)
        if not check_in or not check_out:
            return WhatsAppMessageResponseDTO(
                reply=(
                    "Não consegui identificar as datas. "
                    "Informe no formato: DD/MM/AAAA e DD/MM/AAAA\n"
                    "Exemplo: 15/03/2025 e 18/03/2025"
                ),
                success=True,
            )

        today = date.today()
        if check_in < today:
            return WhatsAppMessageResponseDTO(
                reply="A data de check-in não pode ser no passado. Informe novas datas.",
                success=True,
            )

        if check_in >= check_out:
            return WhatsAppMessageResponseDTO(
                reply="A data de check-out deve ser após o check-in. Informe novas datas.",
                success=True,
            )

        available = self.create_reservation_use_case.check_availability(hotel_id, check_in, check_out)
        if not available:
            return WhatsAppMessageResponseDTO(
                reply="Desculpe, não há quartos disponíveis para este período. Tente outras datas.",
                success=False,
            )

        flow_state["step"] = self.STEP_AWAITING_ROOM_CHOICE
        flow_state["check_in"] = check_in.isoformat()
        flow_state["check_out"] = check_out.isoformat()
        flow_state["available_rooms"] = [
            {
                "number": r.number,
                "room_type": r.room_type,
                "daily_rate": r.daily_rate,
                "max_guests": getattr(r, "max_guests", None),
            }
            for r in available
        ]
        self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)

        room_list = "\n".join(
            f"- {r.number} ({r.room_type}) - R$ {r.daily_rate:.2f}/noite"
            for r in available
        )

        list_items = [
            {
                "id": str(r.get("number")),
                "title": f'{r.get("number")} ({r.get("room_type")})',
                "description": f'R$ {float(r.get("daily_rate") or 0.0):.2f}/noite',
            }
            for r in flow_state.get("available_rooms", [])
        ]
        return WhatsAppMessageResponseDTO(
            reply=(
                f"Quartos disponíveis:\n\n{room_list}\n\n"
                "Escolha uma opção acima (ou digite o número)."
            ),
            success=True,
            message_type="list",
            list_header="Quartos disponíveis",
            list_body="Escolha o quarto",
            list_items=list_items,
        )

    def _handle_create_awaiting_room_choice(
        self, hotel_id: str, phone: str, content_lower: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Process room selection."""
        rooms = flow_state.get("available_rooms", [])
        room_numbers = [r["number"] for r in rooms]

        selected = None
        for rn in room_numbers:
            if rn in content_lower or content_lower.strip() == rn:
                selected = rn
                break

        if not selected:
            return WhatsAppMessageResponseDTO(
                reply=f"Qual quarto? Opções: {', '.join(room_numbers)}",
                success=True,
            )

        flow_state["step"] = self.STEP_AWAITING_NAME
        flow_state["selected_room"] = selected
        self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)

        return WhatsAppMessageResponseDTO(
            reply="Qual o nome do hóspede?",
            success=True,
        )

    def _handle_create_awaiting_name(
        self, hotel_id: str, phone: str, text: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Process guest name input, create reservation PENDING, and ask guests info."""
        name = text.strip()
        if len(name) < 2:
            return WhatsAppMessageResponseDTO(
                reply="Por favor, informe o nome completo do hóspede.",
                success=True,
            )

        check_in = date.fromisoformat(flow_state["check_in"])
        check_out = date.fromisoformat(flow_state["check_out"])
        room_number = flow_state["selected_room"]
        room = next(
            r for r in flow_state["available_rooms"] if r["number"] == room_number
        )

        response = self.create_reservation_use_case.create(
            hotel_id,
            CreateReservationRequestDTO(
                phone=phone,
                check_in=check_in,
                check_out=check_out,
                room_number=room_number,
                guest_name=name,
            ),
        )

        if not response.success:
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return WhatsAppMessageResponseDTO(
                reply=response.message,
                success=False,
            )

        num_nights = (check_out - check_in).days
        total = room["daily_rate"] * num_nights
        requires_payment, allows_without = self._get_payment_config(hotel_id)

        flow_state["guest_name"] = name
        flow_state["reservation_id"] = response.reservation_id
        flow_state["selected_room"] = room_number
        flow_state["total_amount"] = total
        flow_state["requires_payment"] = requires_payment
        flow_state["allows_without"] = allows_without
        flow_state["room_type"] = room.get("room_type")

        # Depois do nome, coletamos quantos hóspedes/crianças.
        max_guests = flow_state.get("available_rooms", [])
        selected = next(
            (r for r in max_guests if r.get("number") == room_number), None
        )
        capacity = int(selected.get("max_guests") or 4) if selected else 4
        capacity = max(1, capacity)

        flow_state["step"] = self.STEP_AWAITING_GUEST_COUNT
        self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)

        return WhatsAppMessageResponseDTO(
            reply=f"Quantos hóspedes vão se hospedar? (ou digite 1 a {capacity})",
            success=True,
            message_type="button",
            buttons=[{"id": str(i), "title": str(i)} for i in range(1, capacity + 1)],
        )

    def _handle_create_awaiting_guest_count(
        self,
        hotel_id: str,
        phone: str,
        content_lower: str,
        flow_state: dict,
    ) -> WhatsAppMessageResponseDTO:
        """Handle guest count input before asking about children."""
        stripped = (content_lower or "").strip()
        if re.fullmatch(r"\d+", stripped):
            num_guests = int(stripped)
        else:
            num_guests = None

        if not num_guests or num_guests < 1:
            return WhatsAppMessageResponseDTO(
                reply="Por favor, informe quantos hóspedes (ex.: 2).",
                success=True,
            )

        flow_state["num_guests"] = num_guests
        flow_state["step"] = self.STEP_AWAITING_CHILDREN
        self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)

        return WhatsAppMessageResponseDTO(
            reply="Vai ter crianças? Responda com SIM ou NÃO (ou digite SIM/NÃO).",
            success=True,
            message_type="button",
            buttons=[{"id": "sim", "title": "SIM"}, {"id": "nao", "title": "NÃO"}],
        )

    def _handle_create_awaiting_children(
        self,
        hotel_id: str,
        phone: str,
        content_lower: str,
        flow_state: dict,
    ) -> WhatsAppMessageResponseDTO:
        """Handle whether the reservation has children."""
        stripped = (content_lower or "").strip()
        if stripped in ("sim", "s", "yes"):
            has_children = True
        elif stripped in ("nao", "não", "n", "no"):
            has_children = False
        else:
            has_children = None

        if has_children is None:
            return WhatsAppMessageResponseDTO(
                reply="Responda se vai ter crianças com SIM ou NÃO (ou digite SIM/NÃO).",
                success=True,
            )

        flow_state["has_children"] = has_children

        if not has_children:
            flow_state["num_children"] = 0
            flow_state["step"] = self.STEP_AWAITING_PAYMENT_CHOICE
            self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)
            return self._finalize_create_reservation_after_guest_details(hotel_id, phone)

        flow_state["step"] = self.STEP_AWAITING_CHILDREN_COUNT
        self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)

        num_guests = int(flow_state.get("num_guests") or 1)
        capacity = max(1, num_guests)
        return WhatsAppMessageResponseDTO(
            reply=f"Quantas crianças? (ou digite 0 a {capacity})",
            success=True,
            message_type="button",
            buttons=[{"id": str(i), "title": str(i)} for i in range(0, capacity + 1)],
        )

    def _handle_create_awaiting_children_count(
        self,
        hotel_id: str,
        phone: str,
        content_lower: str,
        flow_state: dict,
    ) -> WhatsAppMessageResponseDTO:
        """Handle number of children before payment choice."""
        stripped = (content_lower or "").strip()
        if re.fullmatch(r"\d+", stripped):
            num_children = int(stripped)
        else:
            num_children = None

        if num_children is None or num_children < 0:
            return WhatsAppMessageResponseDTO(
                reply="Por favor, informe a quantidade de crianças (ex.: 1).",
                success=True,
            )

        max_children = int(flow_state.get("num_guests") or 1)
        if num_children > max_children:
            num_children = max_children

        flow_state["num_children"] = num_children
        flow_state["step"] = self.STEP_AWAITING_PAYMENT_CHOICE
        self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)
        return self._finalize_create_reservation_after_guest_details(hotel_id, phone)

    def _finalize_create_reservation_after_guest_details(
        self, hotel_id: str, phone: str
    ) -> WhatsAppMessageResponseDTO:
        """Build summary/payment options after guests and children are collected."""
        flow_state = self._get_flow_state(f"{hotel_id}:{phone}") or {}

        guest_name = flow_state.get("guest_name", "Hóspede")
        reservation_id = flow_state.get("reservation_id", "")
        room_number = flow_state.get("selected_room", "")
        total = float(flow_state.get("total_amount") or 0.0)
        room_type = flow_state.get("room_type", "")

        check_in = date.fromisoformat(flow_state["check_in"])
        check_out = date.fromisoformat(flow_state["check_out"])
        num_guests = int(flow_state.get("num_guests") or 1)
        num_children = int(flow_state.get("num_children") or 0)
        has_children = bool(flow_state.get("has_children"))

        summary_lines = [
            "📋 Resumo da reserva:",
            f"- Nome: {guest_name}",
            f"- Hóspedes: {num_guests}",
            f"- Crianças: {num_children if has_children else 0}",
            f"- Check-in: {check_in.strftime('%d/%m/%Y')}",
            f"- Check-out: {check_out.strftime('%d/%m/%Y')}",
            f"- Quarto: {room_number} ({room_type})",
            f"- Total: R$ {total:.2f}",
            "",
        ]

        requires_payment = bool(flow_state.get("requires_payment"))
        allows_without = bool(flow_state.get("allows_without"))

        if "requires_payment" not in flow_state or "allows_without" not in flow_state:
            requires_payment, allows_without = self._get_payment_config(hotel_id)

        if requires_payment:
            payment_msg, is_manual = self._build_payment_message(
                hotel_id, reservation_id, total, guest_name, room_number
            )
            summary_lines.append(payment_msg)
            if is_manual:
                flow_state["step"] = self.STEP_AWAITING_PAYMENT_PROOF
                self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)
                summary_lines.append("")
                summary_lines.append(
                    "📤 Envie seu comprovante de pagamento aqui para confirmarmos sua reserva."
                )
            else:
                self._clear_flow_state(f"{hotel_id}:{phone}")

            return WhatsAppMessageResponseDTO(
                reply="\n".join(summary_lines),
                success=True,
            )

        flow_state["step"] = self.STEP_AWAITING_PAYMENT_CHOICE
        self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)

        if allows_without:
            summary_body = (
                "\n".join(summary_lines)
                + "\n\nComo deseja prosseguir?"
                + "\nEscolha uma opção acima (ou digite 1/2)."
            )
            return WhatsAppMessageResponseDTO(
                reply=summary_body,
                success=True,
                message_type="button",
                buttons=[
                    {"id": "1", "title": "Confirmar e pagar agora"},
                    {"id": "2", "title": "Confirmar sem pagamento imediato"},
                ],
            )

        return WhatsAppMessageResponseDTO(
            reply=(
                "\n".join(summary_lines)
                + "\n\nPara confirmar, efetue o pagamento."
                + "\n\nSe disponível, toque no botão para ver as instruções de pagamento (ou digite 1)."
            ),
            success=True,
            message_type="button",
            buttons=[{"id": "1", "title": "Ver instruções de pagamento"}],
        )

    def _handle_create_awaiting_payment_choice(
        self, hotel_id: str, phone: str, content_lower: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Process payment choice (Passo 10 - Fase 0, conforme config do hotel)."""
        if self._is_negative_confirmation(content_lower) or "cancelar" in content_lower:
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return WhatsAppMessageResponseDTO(
                reply="❌ Reserva cancelada. Se precisar de algo mais, me avise.",
                success=True,
            )

        _, allows_without = self._get_payment_config(hotel_id)

        # Opção 1: Pagar agora (Fase 0 ou Fase 1 - link)
        if self._is_pay_now_choice(content_lower):
            reservation_id = flow_state.get("reservation_id", "")
            guest_name = flow_state.get("guest_name", "Reserva")
            room_number = flow_state.get("selected_room", "")
            reservation = self.reservation_repository.find_by_phone_number(phone, hotel_id)
            total = reservation.total_amount if reservation else 0.0
            payment_msg, is_manual = self._build_payment_message(
                hotel_id, reservation_id, total, guest_name, room_number
            )
            if is_manual:
                flow_state["step"] = self.STEP_AWAITING_PAYMENT_PROOF
                self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)
                return WhatsAppMessageResponseDTO(
                    reply=f"✅ Reserva criada!\n\n{payment_msg}\n\n"
                    "📤 Envie seu comprovante de pagamento aqui para confirmarmos sua reserva.",
                    success=True,
                )
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return WhatsAppMessageResponseDTO(
                reply=f"✅ Reserva criada!\n\n{payment_msg}",
                success=True,
            )

        # Opção 2: Confirmar sem pagamento (só se hotel permite)
        if allows_without and self._is_confirm_without_payment_choice(content_lower):
            self._clear_flow_state(f"{hotel_id}:{phone}")
            response = self.confirm_reservation_use_case.confirm(
                hotel_id, ConfirmReservationRequestDTO(phone=phone)
            )
            return WhatsAppMessageResponseDTO(
                reply=f"✅ {response.message}",
                success=response.success,
            )

        if allows_without:
            return WhatsAppMessageResponseDTO(
                reply="Como deseja prosseguir?\nEscolha uma opção acima (ou digite 1/2).",
                success=True,
                message_type="button",
                buttons=[
                    {"id": "1", "title": "Confirmar e pagar agora"},
                    {"id": "2", "title": "Confirmar sem pagamento imediato"},
                ],
            )
        return WhatsAppMessageResponseDTO(
            reply=(
                "Para confirmar sua reserva, efetue o pagamento.\n"
                "Se disponível, toque no botão para ver as instruções (ou digite 1)."
            ),
            success=True,
            message_type="button",
            buttons=[{"id": "1", "title": "Ver instruções de pagamento"}],
        )

    def _handle_create_awaiting_payment_proof(
        self,
        hotel_id: str,
        phone: str,
        text: str,
        flow_state: dict,
        has_media: bool = False,
    ) -> WhatsAppMessageResponseDTO:
        """
        Recebe comprovante de pagamento (texto ou mídia).
        Cria Payment PENDING manual para o hotel confirmar no painel.
        Perguntas laterais (políticas, horários, etc.) são respondidas pela IA
        sem sair do fluxo.
        """
        if not (text.strip() or has_media):
            return WhatsAppMessageResponseDTO(
                reply="Por favor, envie o comprovante de pagamento (texto ou imagem).",
                success=True,
            )

        # Perguntas laterais: responde via IA e mantém o fluxo
        content_lower = text.lower()
        if self._is_lateral_question(content_lower, has_media):
            try:
                ai_reply = self.conversation_use_case.execute(hotel_id, phone, text)
                reminder = (
                    "\n\n---\n"
                    "💳 Quando estiver pronto, envie o comprovante de pagamento para confirmarmos sua reserva."
                )
                return WhatsAppMessageResponseDTO(
                    reply=f"{ai_reply}{reminder}",
                    success=True,
                )
            except Exception as exc:
                return WhatsAppMessageResponseDTO(
                    reply=(
                        "Desculpe, não consegui processar sua pergunta no momento. "
                        "Por favor, envie o comprovante de pagamento para confirmarmos sua reserva."
                    ),
                    success=False,
                    error=str(exc),
                )

        reservation_id = flow_state.get("reservation_id", "")
        if not reservation_id:
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return WhatsAppMessageResponseDTO(
                reply="Não encontramos sua reserva. Por favor, inicie uma nova reserva.",
                success=False,
            )

        reservation = self.reservation_repository.find_by_id(reservation_id, hotel_id)
        total = reservation.total_amount if reservation else 0.0

        payment_id = str(uuid.uuid4())
        transaction_id = f"comprovante_whatsapp_{int(time.time())}"
        payment = Payment(
            payment_id=payment_id,
            reservation_id=reservation_id,
            hotel_id=hotel_id,
            amount=total,
            status="PENDING",
            payment_method="manual",
            transaction_id=transaction_id,
        )
        self.payment_repository.save(hotel_id, payment)

        self._clear_flow_state(f"{hotel_id}:{phone}")
        return WhatsAppMessageResponseDTO(
            reply=(
                "✅ Recebemos seu comprovante!\n\n"
                "Sua reserva será confirmada em breve após a verificação do pagamento. "
                "Você receberá uma confirmação assim que estiver tudo certo."
            ),
            success=True,
        )

    def _get_payment_config(self, hotel_id: str) -> tuple[bool, bool]:
        """
        Retorna (requires_payment_for_confirmation, allows_reservation_without_payment).
        Se não houver hotel configurado, usa defaults: (False, True) = oferece ambas opções.
        """
        hotel = self.hotel_repository.get_active_hotel(hotel_id)
        if not hotel:
            return False, True
        return (
            getattr(hotel, "requires_payment_for_confirmation", False),
            getattr(hotel, "allows_reservation_without_payment", True),
        )

    def _build_payment_message(
        self,
        hotel_id: str,
        reservation_id: str,
        total: float,
        guest_name: str,
        room_number: str,
    ) -> tuple[str, bool]:
        """
        Monta mensagem de pagamento: Fase 1/2 (link) se disponível, senão Fase 0 (manual).
        Fase 2: cria Payment e persiste transaction_id para webhook.
        Retorna (mensagem, is_manual). is_manual=True quando não há link (PIX manual).
        """
        amount_cents = int(round(total * 100))
        description = f"Reserva - {guest_name} - Quarto {room_number}"

        payment_id = str(uuid.uuid4())
        result = self.payment_provider.create_checkout_link(
            reservation_id=reservation_id,
            amount_cents=amount_cents,
            description=description,
            currency="brl",
            payment_id=payment_id,
        )
        if result:
            url, session_id = result
            payment = Payment(
                payment_id=payment_id,
                reservation_id=reservation_id,
                hotel_id=hotel_id,
                amount=total,
                status="PENDING",
                payment_method="stripe",
                transaction_id=session_id,
            )
            self.payment_repository.save(hotel_id, payment)

            # Mensagem com PIX + Cartão (preferência do cliente).
            pix_instructions = self._get_payment_instructions(hotel_id)
            return (
                "Para confirmar sua reserva, você pode pagar com cartão ou PIX:\n\n"
                f"🔗 Cartão (pague pelo link):\n{url}\n\n"
                f"{pix_instructions}\n\n"
                "A reserva será confirmada automaticamente após o pagamento do cartão, "
                "ou após a verificação do comprovante do PIX.",
                False,
            )

        instructions = self._get_payment_instructions(hotel_id)
        return (
            "Para confirmar sua reserva, efetue o pagamento:\n\n"
            f"{instructions}\n\n"
            "A reserva será confirmada após a verificação do comprovante.",
            True,
        )

    def _try_handle_payment_proof_without_flow_state(
        self,
        hotel_id: str,
        phone: str,
    ) -> WhatsAppMessageResponseDTO | None:
        """
        Quando não há flow_state (ex: cartão disponível e fluxo foi limpo),
        mas o usuário enviou mídia, tentamos interpretar como comprovante de PIX
        para a reserva ainda PENDING.
        """
        try:
            from app.domain.entities.reservation.reservation_status import ReservationStatus

            reservation = self.reservation_repository.find_by_phone_number(phone, hotel_id)
            if not reservation:
                return None
            if getattr(reservation, "status", None) != ReservationStatus.PENDING:
                return None

            total = float(getattr(reservation, "total_amount", 0.0) or 0.0)
            reservation_id = getattr(reservation, "id", None)
            if not reservation_id:
                return None

            payment_id = str(uuid.uuid4())
            transaction_id = f"comprovante_whatsapp_{int(time.time())}"
            payment = Payment(
                payment_id=payment_id,
                reservation_id=reservation_id,
                hotel_id=hotel_id,
                amount=total,
                status="PENDING",
                payment_method="manual",
                transaction_id=transaction_id,
            )
            self.payment_repository.save(hotel_id, payment)

            return WhatsAppMessageResponseDTO(
                reply=(
                    "✅ Recebemos seu comprovante!\n\n"
                    "Sua reserva será confirmada em breve após a verificação do pagamento. "
                    "Você receberá uma confirmação assim que estiver tudo certo."
                ),
                success=True,
            )
        except Exception:
            return None

    def _get_payment_instructions(self, hotel_id: str) -> str:
        """Retorna instruções de pagamento (Fase 0: manual)."""
        import os
        env_instructions = os.getenv("PAYMENT_INSTRUCTIONS")
        if env_instructions:
            # Se o admin configurou um placeholder, preenche com a melhor chave disponível.
            if "{pix_key}" in env_instructions:
                return env_instructions.format(pix_key=self._get_pix_key_for_hotel(hotel_id))
            return env_instructions

        return self.DEFAULT_PAYMENT_INSTRUCTIONS_TEMPLATE.format(
            pix_key=self._get_pix_key_for_hotel(hotel_id)
        )

    def _get_pix_key_for_hotel(self, hotel_id: str) -> str:
        """
        Retorna uma chave PIX para instruções Fase 0.

        Como o modelo de Hotel não persiste chave PIX explicitamente,
        usamos o contato do hotel como chave quando disponível.
        """
        try:
            hotel = self.hotel_repository.get_active_hotel(hotel_id)
            pix_key = getattr(hotel, "pix_key", None)
            if pix_key:
                return str(pix_key)
            contact_phone = getattr(hotel, "contact_phone", None)
            if contact_phone:
                return str(contact_phone)
        except Exception:
            pass

        # Fallback antigo (para não quebrar comportamento).
        return "contato@hotel.com"

    # --- 6.1 Pré-check-in ---
    @staticmethod
    def _is_pre_checkin_intent(content_lower: str) -> bool:
        return any(
            kw in content_lower
            for kw in ["pré-checkin", "pre checkin", "precheckin", "documentos", "registrar cpf"]
        )

    def _start_pre_checkin_flow(
        self, hotel_id: str, phone: str
    ) -> WhatsAppMessageResponseDTO:
        reservation = self.reservation_repository.find_by_phone_number(phone, hotel_id)
        if not reservation:
            return WhatsAppMessageResponseDTO(
                reply="Nenhuma reserva encontrada. Faça uma reserva primeiro.",
                success=False,
            )
        if getattr(reservation, "pre_checkin_completed_at", None):
            return WhatsAppMessageResponseDTO(
                reply="Você já concluiu o pré-check-in.",
                success=True,
            )
        flow_state = {
            "action": self.PRE_CHECKIN_ACTION,
            "step": self.STEP_AWAITING_DOCUMENT,
        }
        self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=600)
        return WhatsAppMessageResponseDTO(
            reply="📋 Pré-check-in\n\nInforme seu CPF (apenas números):",
            success=True,
        )

    def _handle_pre_checkin_flow(
        self, hotel_id: str, phone: str, text: str, content_lower: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        step = flow_state.get("step", self.STEP_AWAITING_DOCUMENT)
        if step == self.STEP_AWAITING_DOCUMENT:
            doc = (text or "").replace(".", "").replace("-", "").strip()
            if len(doc) < 11:
                return WhatsAppMessageResponseDTO(
                    reply="CPF inválido. Informe 11 dígitos:",
                    success=True,
                )
            flow_state["guest_document"] = doc
            flow_state["step"] = self.STEP_AWAITING_ARRIVAL_TIME
            self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=600)
            return WhatsAppMessageResponseDTO(
                reply="Horário estimado de chegada? (ex: 14h, 15h30)",
                success=True,
            )
        if step == self.STEP_AWAITING_ARRIVAL_TIME:
            from app.application.use_cases.pre_checkin import PreCheckInRequestDTO
            arrival = (text or "").strip() or None
            resp = self.pre_checkin_use_case.execute(hotel_id, PreCheckInRequestDTO(
                phone=phone,
                guest_document=flow_state.get("guest_document", ""),
                estimated_arrival_time=arrival,
            ))
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return WhatsAppMessageResponseDTO(reply=resp.message, success=resp.success)
        self._clear_flow_state(f"{hotel_id}:{phone}")
        return WhatsAppMessageResponseDTO(reply="Pré-check-in cancelado.", success=True)

    # --- 6.6 Resolução de problemas ---
    @staticmethod
    def _is_support_ticket_intent(content_lower: str) -> bool:
        return any(
            kw in content_lower
            for kw in [
                "problema", "não funciona", "nao funciona", "quebrado",
                "ar condicionado", "ar-condicionado", "ar condicionado não",
                "vazamento", "preciso de ajuda", "reportar",
            ]
        )

    def _handle_support_ticket(self, hotel_id: str, phone: str, text: str) -> WhatsAppMessageResponseDTO:
        from app.application.use_cases.create_support_ticket import CreateSupportTicketRequestDTO
        category = "GENERAL"
        if "ar condicionado" in text.lower() or "ar-condicionado" in text.lower():
            category = "AR_CONDICIONADO"
        elif "vazamento" in text.lower():
            category = "VAZAMENTO"
        resp = self.support_ticket_use_case.execute(
            hotel_id,
            CreateSupportTicketRequestDTO(
                phone=phone,
                description=text[:500],
                category=category,
            ),
        )
        return WhatsAppMessageResponseDTO(reply=resp.message, success=resp.success)

    # --- 6.5 Pedidos durante estadia ---
    @staticmethod
    def _is_room_order_intent(content_lower: str) -> bool:
        return any(
            kw in content_lower
            for kw in ["room service", "cardápio", "cardapio", "pedido", "quero pedir"]
        )

    def _handle_room_order(self, hotel_id: str, phone: str, content_lower: str) -> WhatsAppMessageResponseDTO:
        if "cardápio" in content_lower or "cardapio" in content_lower or "menu" in content_lower:
            from app.application.use_cases.room_order import RoomOrderUseCase
            return WhatsAppMessageResponseDTO(
                reply=RoomOrderUseCase.get_menu_text(),
                success=True,
            )
        # Parse simples: "café 2, água 3" -> items
        from app.application.use_cases.room_order import RoomOrderUseCase, OrderItemDTO, RoomOrderRequestDTO
        items = []
        menu_map = {m["name"].lower(): m for m in RoomOrderUseCase.MENU}
        for part in content_lower.replace(" e ", ",").split(","):
            part = part.strip()
            for name, info in menu_map.items():
                if name in part:
                    qty = 1
                    for w in part.split():
                        if w.isdigit():
                            qty = int(w)
                            break
                    items.append(OrderItemDTO(
                        name=info["name"],
                        quantity=qty,
                        unit_price=info["price"],
                    ))
                    break
        if not items:
            return WhatsAppMessageResponseDTO(
                reply="Não entendi o pedido. Envie CARDÁPIO para ver opções.",
                success=True,
            )
        resp = self.room_order_use_case.execute(hotel_id, RoomOrderRequestDTO(phone=phone, items=items))
        return WhatsAppMessageResponseDTO(reply=resp.message, success=resp.success)

    @staticmethod
    def _is_pay_now_choice(content_lower: str) -> bool:
        stripped = content_lower.strip()
        if stripped == "1":
            return True
        return any(
            x in content_lower
            for x in ["pagar", "pagamento", "confirmar e pagar", "pagar agora"]
        )

    @staticmethod
    def _is_confirm_without_payment_choice(content_lower: str) -> bool:
        stripped = content_lower.strip()
        if stripped == "2":
            return True
        return any(
            x in content_lower
            for x in [
                "sem pagamento",
                "confirmar sem pagamento",
                "sem pagamento imediato",
            ]
        )

    @staticmethod
    def _is_lateral_question(content_lower: str, has_media: bool) -> bool:
        """
        Detecta se a mensagem é uma pergunta lateral (ex: políticas, horários)
        e não um comprovante de pagamento.
        Imagens/documentos são sempre tratados como comprovante.
        """
        if has_media:
            return False
        stripped = content_lower.strip()
        if not stripped or len(stripped) < 3:
            return False
        # Padrões de pergunta: palavras interrogativas e tópicos comuns
        question_patterns = [
            "qual ", "quais ", "como ", "quando ", "onde ", "por que ", "porque ",
            "posso ", "pode ", "podem ", "horário", "horarios", "política", "políticas",
            "cancelamento", "cancelar", "café", "cafe da manhã", "check-in", "check-out",
            "serviço", "serviços", "wifi", "estacionamento", "pets", "pet ",
            "aceita ", "tem ", "há ", "existe ", "existem ",
            "me inform", "me diz", "me conta", "gostaria de sab", "queria sab",
        ]
        if any(p in content_lower for p in question_patterns):
            return True
        if stripped.endswith("?"):
            return True
        # Textos longos (>40 chars) sem padrão de comprovante tendem a ser perguntas
        proof_patterns = ["pix", "transferência", "transferencia", "paguei", "pago", "comprovante"]
        if len(stripped) > 40 and not any(p in content_lower for p in proof_patterns):
            return True
        return False

    @staticmethod
    def _is_create_reservation_intent(content_lower: str) -> bool:
        """Detecta intenção de fazer nova reserva (fluxo guiado com pagamento)."""
        create_keywords = [
            "fazer reserva",
            "quero reservar",
            "reservar quarto",
            "fazer uma reserva",
            "quero fazer reserva",
            "gostaria de reservar",
            "desejo reservar",
            "posso reservar",
            "quero uma reserva",
            "realizar reserva",
            "efetuar reserva",
            "reserva para",
            "reservar para",
            "quanto fica",
            "quanto fica no total",
            "pode ser o",
            "quarto standard",
            "quarto executive",
        ]
        if any(kw in content_lower for kw in create_keywords):
            return True

        # "reserva" ou "booking" sem ser cancelar/confirmar/pergunta existente
        if "reserva" in content_lower or "booking" in content_lower:
            if "cancelar" in content_lower:
                return False  # vai para cancel flow
            if "confirm" in content_lower:
                return False  # vai para confirm flow
            question_about_existing = any(
                q in content_lower
                for q in [
                    "minha reserva",
                    "status da reserva",
                    "qual reserva",
                    "ver reserva",
                    "consultar reserva",
                ]
            )
            if not question_about_existing:
                return True

        return False

    def _start_cancel_reservation_flow(
        self, hotel_id: str, phone: str
    ) -> WhatsAppMessageResponseDTO:
        """Initiate reservation cancellation flow."""
        response = self.cancel_reservation_use_case.prepare_cancellation(
            hotel_id,
            CancelReservationRequestDTO(phone=phone),
        )

        if not response.success:
            return WhatsAppMessageResponseDTO(reply=response.message, success=False)

        if not response.can_cancel:
            return WhatsAppMessageResponseDTO(reply=response.message, success=True)

        flow_state = {
            "action": self.CANCEL_RESERVATION_ACTION,
            "step": self.STEP_SUMMARY_DISPLAYED,
        }
        self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)

        reply = (
            (response.summary or "Resumo da reserva")
            + "\n\nDeseja realmente cancelar?\nEscolha: SIM ou NÃO (ou digite SIM/NÃO)"
        )

        return WhatsAppMessageResponseDTO(
            reply=reply,
            success=True,
            message_type="button",
            buttons=[
                {"id": "sim", "title": "SIM"},
                {"id": "nao", "title": "NÃO"},
            ],
        )

    def _handle_cancel_reservation_flow(
        self, hotel_id: str, phone: str, content_lower: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Handle ongoing cancellation flow."""
        if self._is_negative_confirmation(content_lower):
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return WhatsAppMessageResponseDTO(
                reply="Operação cancelada. Sua reserva permanece ativa.",
                success=True,
            )

        if self._is_positive_confirmation(content_lower):
            self._clear_flow_state(f"{hotel_id}:{phone}")
            response = self.cancel_reservation_use_case.cancel(
                hotel_id,
                CancelReservationRequestDTO(phone=phone),
            )
            return WhatsAppMessageResponseDTO(
                reply=f"✅ {response.message}",
                success=response.success,
            )

        return WhatsAppMessageResponseDTO(
            reply="Escolha: SIM para cancelar ou NÃO para manter a reserva (ou digite SIM/NÃO).",
            success=True,
            message_type="button",
            buttons=[
                {"id": "sim", "title": "SIM"},
                {"id": "nao", "title": "NÃO"},
            ],
        )

    def _start_confirm_reservation_flow(
        self, hotel_id: str, phone: str
    ) -> WhatsAppMessageResponseDTO:
        """Initiate reservation confirmation flow."""
        response = self.confirm_reservation_use_case.prepare_confirmation(
            hotel_id,
            ConfirmReservationRequestDTO(phone=phone),
        )

        if not response.success:
            return WhatsAppMessageResponseDTO(reply=response.message, success=False)

        if not response.can_confirm:
            return WhatsAppMessageResponseDTO(reply=response.message, success=True)

        # Get formatted summary via use case (encapsula acesso ao repositório)
        formatted_summary = self.confirm_reservation_use_case.get_formatted_summary_for_phone(
            hotel_id, phone
        )
        if not formatted_summary:
            formatted_summary = response.summary or "Resumo da reserva"

        flow_state = {
            "action": self.CONFIRM_RESERVATION_ACTION,
            "step": self.STEP_SUMMARY_DISPLAYED,
        }
        self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)

        reply = (
            f"{formatted_summary}\n\nTudo está correto?\n"
            "Escolha: SIM / NÃO / EDITAR (ou digite SIM/NÃO/EDITAR)"
        )

        return WhatsAppMessageResponseDTO(
            reply=reply,
            success=True,
            message_type="button",
            buttons=[
                {"id": "sim", "title": "SIM"},
                {"id": "nao", "title": "NÃO"},
                {"id": "editar", "title": "EDITAR"},
            ],
        )

    def _start_extend_reservation_flow(
        self, hotel_id: str, phone: str
    ) -> WhatsAppMessageResponseDTO:
        """Initiate reservation extension flow."""
        response = self.extend_reservation_use_case.prepare_extension(
            hotel_id,
            ExtendReservationRequestDTO(phone=phone),
        )

        if not response.success:
            return WhatsAppMessageResponseDTO(reply=response.message, success=False)

        if not response.can_extend:
            return WhatsAppMessageResponseDTO(reply=response.message, success=True)

        flow_state = {
            "action": self.EXTEND_RESERVATION_ACTION,
            "step": self.STEP_AWAITING_NEW_CHECKOUT,
        }
        self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)

        reply_parts = [
            response.summary or "Resumo da reserva",
            "\n📅 " + response.message,
        ]

        return WhatsAppMessageResponseDTO(
            reply="\n".join(reply_parts),
            success=True,
        )

    def _handle_extend_reservation_flow(
        self, hotel_id: str, phone: str, text: str, content_lower: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Handle ongoing extension flow."""
        if self._is_negative_confirmation(content_lower) or "cancelar" in content_lower:
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return WhatsAppMessageResponseDTO(
                reply="Operação cancelada. Sua reserva permanece como estava.",
                success=True,
            )

        current_step = flow_state.get("step", self.STEP_AWAITING_NEW_CHECKOUT)
        if current_step == self.STEP_AWAITING_NEW_CHECKOUT:
            return self._handle_extend_awaiting_new_checkout(
                hotel_id, phone, text, flow_state
            )

        # Step inconsistente (ex: TTL expirou entre mensagens).
        return self._context_lost_response(hotel_id, phone)

    def _parse_single_date_from_text(self, text: str) -> date | None:
        """Extrai uma data do texto. Retorna date ou None."""
        matches = re.findall(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})", text)
        if not matches:
            return None

        def to_date(m):
            d, mo, y = int(m[0]), int(m[1]), int(m[2])
            if y < 100:
                y += 2000
            return date(y, mo, d)

        try:
            return to_date(matches[0])
        except (ValueError, IndexError):
            return None

    def _handle_extend_awaiting_new_checkout(
        self, hotel_id: str, phone: str, text: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Process new checkout date input in extend flow."""
        new_checkout = self._parse_single_date_from_text(text)
        if not new_checkout:
            return WhatsAppMessageResponseDTO(
                reply=(
                    "Não consegui identificar a data. "
                    "Informe no formato DD/MM/AAAA\n"
                    "Exemplo: 25/04/2025"
                ),
                success=True,
            )

        response = self.extend_reservation_use_case.extend(
            hotel_id,
            ExtendReservationRequestDTO(phone=phone, new_checkout=new_checkout),
        )

        self._clear_flow_state(f"{hotel_id}:{phone}")

        return WhatsAppMessageResponseDTO(
            reply=response.message,
            success=response.success,
        )

    def _handle_confirm_reservation_flow(
        self, hotel_id: str, phone: str, text: str, content_lower: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Handle ongoing confirmation flow."""
        current_step = flow_state.get("step", self.STEP_SUMMARY_DISPLAYED)

        if current_step == self.STEP_SUMMARY_DISPLAYED:
            return self._handle_summary_response(
                hotel_id, phone, content_lower, flow_state
            )

        if current_step == self.STEP_AWAITING_EDIT_CHOICE:
            return self._handle_edit_choice(
                hotel_id, phone, text, content_lower, flow_state
            )

        if current_step == self.STEP_AWAITING_ROOM_SELECTION:
            return self._handle_room_selection(
                hotel_id, phone, content_lower, flow_state
            )

        if current_step == self.STEP_AWAITING_NEW_DATES:
            return self._handle_awaiting_new_dates(
                hotel_id, phone, text, flow_state
            )

        # Step inconsistente (ex: TTL expirou entre mensagens).
        return self._context_lost_response(hotel_id, phone)

    def _handle_summary_response(
        self, hotel_id: str, phone: str, content_lower: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Handle response to summary (SIM/NÃO/EDITAR)."""
        if self._is_negative_confirmation(content_lower):
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return WhatsAppMessageResponseDTO(
                reply="❌ Cancelado. Se precisar de algo mais, me avise.",
                success=True,
            )

        if self._is_positive_confirmation(content_lower):
            self._clear_flow_state(f"{hotel_id}:{phone}")
            response = self.confirm_reservation_use_case.confirm(
                hotel_id,
                ConfirmReservationRequestDTO(phone=phone),
            )
            return WhatsAppMessageResponseDTO(
                reply=f"✅ {response.message}",
                success=response.success,
            )

        if self._is_edit_request(content_lower):
            flow_state["step"] = self.STEP_AWAITING_EDIT_CHOICE
            self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)
            return WhatsAppMessageResponseDTO(
                reply=(
                    "O que deseja alterar?\n"
                    "Escolha: QUARTO / DATAS / CANCELAR (ou digite QUARTO/DATAS/CANCELAR)"
                ),
                success=True,
                message_type="button",
                buttons=[
                    {"id": "quarto", "title": "QUARTO"},
                    {"id": "datas", "title": "DATAS"},
                    {"id": "cancelar", "title": "CANCELAR"},
                ],
            )

        return WhatsAppMessageResponseDTO(
            reply=(
                "Escolha: SIM para confirmar, NÃO para cancelar ou EDITAR para alterar.\n"
                "(ou digite SIM/NÃO/EDITAR)"
            ),
            success=True,
            message_type="button",
            buttons=[
                {"id": "sim", "title": "SIM"},
                {"id": "nao", "title": "NÃO"},
                {"id": "editar", "title": "EDITAR"},
            ],
        )

    def _handle_edit_choice(
        self,
        hotel_id: str,
        phone: str,
        text: str,
        content_lower: str,
        flow_state: dict,
    ) -> WhatsAppMessageResponseDTO:
        """Handle edit choice (QUARTO/DATAS/CANCELAR)."""
        if self._is_negative_confirmation(content_lower) or "cancelar" in content_lower:
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return WhatsAppMessageResponseDTO(
                reply="❌ Edição cancelada. Se precisar de mais algo, me avise.",
                success=True,
            )

        if "quarto" in content_lower:
            reservation = self.reservation_repository.find_by_phone_number(
                phone, hotel_id
            )
            if not reservation or not reservation.stay_period:
                self._clear_flow_state(f"{hotel_id}:{phone}")
                return WhatsAppMessageResponseDTO(
                    reply="Não consegui localizar os dados da reserva.",
                    success=False,
                )

            available_rooms = self.room_repository.find_available(
                hotel_id,
                reservation.stay_period.start,
                reservation.stay_period.end,
                exclude_room=reservation.room_number,
            )

            if not available_rooms:
                return WhatsAppMessageResponseDTO(
                    reply="Desculpe, não há quartos disponíveis para este período.",
                    success=False,
                )

            flow_state["step"] = self.STEP_AWAITING_ROOM_SELECTION
            flow_state["available_rooms"] = [room.number for room in available_rooms]
            self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)

            room_list = "\n".join(
                [
                    f"- {room.number} ({room.room_type}) - R$ {room.daily_rate:.2f}/noite"
                    for room in available_rooms
                ]
            )
            reply = f"Quartos disponíveis:\n\n{room_list}\n\nQual você escolhe? (ou digite o número)"

            # Meta: lista com até 10 itens.
            list_items = []
            for room in available_rooms[:10]:
                list_items.append(
                    {
                        "id": str(room.number),
                        "title": f"Quarto {room.number}",
                        "description": f"{room.room_type} - R$ {room.daily_rate:.2f}/noite",
                    }
                )

            return WhatsAppMessageResponseDTO(
                reply=reply,
                success=True,
                message_type="list",
                list_header="Quartos disponíveis",
                list_body="Selecione uma opção",
                list_items=list_items,
            )

        if "data" in content_lower or "datas" in content_lower:
            reservation = self.reservation_repository.find_by_phone_number(
                phone, hotel_id
            )
            if not reservation or not reservation.stay_period or not reservation.room_number:
                self._clear_flow_state(f"{hotel_id}:{phone}")
                return WhatsAppMessageResponseDTO(
                    reply="Não consegui localizar os dados da reserva.",
                    success=False,
                )

            flow_state["step"] = self.STEP_AWAITING_NEW_DATES
            self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)
            return WhatsAppMessageResponseDTO(
                reply=(
                    "📅 Informe as novas datas da estadia.\n\n"
                    "Exemplo: 20/04/2025 e 23/04/2025\n"
                    "Ou: 20/04/2025 a 23/04/2025"
                ),
                success=True,
            )

        return WhatsAppMessageResponseDTO(
            reply="Escolha: QUARTO / DATAS / CANCELAR (ou digite QUARTO/DATAS/CANCELAR)",
            success=True,
            message_type="button",
            buttons=[
                {"id": "quarto", "title": "QUARTO"},
                {"id": "datas", "title": "DATAS"},
                {"id": "cancelar", "title": "CANCELAR"},
            ],
        )

    def _handle_awaiting_new_dates(
        self, hotel_id: str, phone: str, text: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Process new dates input in edit flow."""
        reservation = self.reservation_repository.find_by_phone_number(phone, hotel_id)
        if not reservation or not reservation.stay_period or not reservation.room_number:
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return WhatsAppMessageResponseDTO(
                reply="Não consegui localizar os dados da reserva.",
                success=False,
            )

        check_in, check_out = self._parse_dates_from_text(text)
        if not check_in or not check_out:
            return WhatsAppMessageResponseDTO(
                reply=(
                    "Não consegui identificar as datas. "
                    "Informe no formato: DD/MM/AAAA e DD/MM/AAAA\n"
                    "Exemplo: 20/04/2025 e 23/04/2025"
                ),
                success=True,
            )

        today = date.today()
        if check_in < today:
            return WhatsAppMessageResponseDTO(
                reply="A data de check-in não pode ser no passado. Informe novas datas.",
                success=True,
            )

        if check_in >= check_out:
            return WhatsAppMessageResponseDTO(
                reply="A data de check-out deve ser após o check-in. Informe novas datas.",
                success=True,
            )

        if not self.room_repository.is_available(
            hotel_id,
            reservation.room_number,
            check_in,
            check_out,
            exclude_reservation_id=reservation.id,
        ):
            return WhatsAppMessageResponseDTO(
                reply=f"O quarto {reservation.room_number} não está disponível para este período. Tente outras datas.",
                success=False,
            )

        room = self.room_repository.get_by_number(hotel_id, reservation.room_number)
        if not room:
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return WhatsAppMessageResponseDTO(
                reply="Não foi possível obter a diária do quarto.",
                success=False,
            )

        try:
            new_period = StayPeriod(check_in, check_out)
        except ValueError as e:
            return WhatsAppMessageResponseDTO(
                reply=str(e),
                success=False,
            )

        try:
            reservation.change_dates(new_period, room.daily_rate)
            self.reservation_repository.save(reservation, hotel_id)
        except exceptions.InvalidDatesChangeState as e:
            return WhatsAppMessageResponseDTO(
                reply=str(e),
                success=False,
            )

        # Volta ao resumo para nova confirmação
        flow_state["step"] = self.STEP_SUMMARY_DISPLAYED
        self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)

        formatted_summary = self.confirm_reservation_use_case.get_formatted_summary_for_phone(
            hotel_id, phone
        )
        reply_parts = [
            formatted_summary or "Resumo atualizado:",
            "\n✅ Datas alteradas com sucesso!",
            "\nTudo está correto agora?",
            "Escolha: SIM / NÃO / EDITAR (ou digite SIM/NÃO/EDITAR)",
        ]
        return WhatsAppMessageResponseDTO(
            reply="\n".join(reply_parts),
            success=True,
            message_type="button",
            buttons=[
                {"id": "sim", "title": "SIM"},
                {"id": "nao", "title": "NÃO"},
                {"id": "editar", "title": "EDITAR"},
            ],
        )

    def _handle_room_selection(
        self, hotel_id: str, phone: str, content_lower: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Handle room selection."""
        available_rooms = flow_state.get("available_rooms", [])
        
        # Try to extract room number from content
        selected_room = None
        for room in available_rooms:
            if room in content_lower:
                selected_room = room
                break

        if not selected_room:
            return WhatsAppMessageResponseDTO(
                reply=f"Qual quarto? Opcoes: {', '.join(available_rooms)}",
                success=True,
            )

        reservation = self.reservation_repository.find_by_phone_number(phone, hotel_id)
        if not reservation:
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return WhatsAppMessageResponseDTO(
                reply="Não consegui localizar os dados da reserva.",
                success=False,
            )

        if not reservation.stay_period:
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return WhatsAppMessageResponseDTO(
                reply="Não consegui localizar os dados da reserva.",
                success=False,
            )

        # Validar disponibilidade antes de chamar domínio
        if not self.room_repository.is_available(
            hotel_id,
            selected_room,
            reservation.stay_period.start,
            reservation.stay_period.end,
        ):
            return WhatsAppMessageResponseDTO(
                reply=f"Quarto {selected_room} não está disponível para este período.",
                success=False,
            )

        try:
            reservation.change_room(selected_room)
            self.reservation_repository.save(reservation, hotel_id)
        except exceptions.InvalidRoomChangeState as e:
            return WhatsAppMessageResponseDTO(
                reply=str(e),
                success=False,
            )

        self._clear_flow_state(f"{hotel_id}:{phone}")

        return WhatsAppMessageResponseDTO(
            reply=f"✅ Quarto {selected_room} selecionado. Reserva confirmada!",
            success=True,
        )

    @staticmethod
    def _is_cancel_reservation_intent(content_lower: str) -> bool:
        stripped = content_lower.strip()
        if stripped in ("cancelar", "cancel"):
            return True
        return any(
            keyword in content_lower
            for keyword in [
                "cancelar reserva",
                "cancelar minha reserva",
                "quero cancelar",
                "cancelar a reserva",
            ]
        )

    @staticmethod
    def _is_checkout_intent(content_lower: str) -> bool:
        return any(
            keyword in content_lower
            for keyword in ["checkout", "check-out", "encerrar hospedagem"]
        )

    @staticmethod
    def _is_confirm_reservation_intent(content_lower: str) -> bool:
        has_confirm = "confirm" in content_lower
        has_reservation = "reserva" in content_lower or "booking" in content_lower
        return has_confirm and has_reservation

    @staticmethod
    def _is_extend_reservation_intent(content_lower: str) -> bool:
        return any(
            keyword in content_lower
            for keyword in [
                "estender",
                "estender estadia",
                "ficar mais",
                "prorrogar",
                "alongar estadia",
            ]
        )

    @staticmethod
    def _is_positive_confirmation(content_lower: str) -> bool:
        return any(
            keyword in content_lower
            for keyword in ["sim", "confirmo", "confirmar", "ok", "yes", "y"]
        )

    @staticmethod
    def _is_negative_confirmation(content_lower: str) -> bool:
        stripped = content_lower.strip()
        if stripped in ("n", "no", "nao", "não"):
            return True
        return any(
            kw in content_lower
            for kw in ["cancelar", "cancela"]
        )

    @staticmethod
    def _is_edit_request(content_lower: str) -> bool:
        return "editar" in content_lower or "edit" in content_lower

    def _get_flow_state(self, phone: str) -> dict | None:
        return self.cache_repository.get(f"{self.FLOW_KEY_PREFIX}{phone}")

    def _set_flow_state(self, phone: str, state: dict, ttl_seconds: int = 900) -> None:
        self.cache_repository.set(f"{self.FLOW_KEY_PREFIX}{phone}", state, ttl_seconds=ttl_seconds)

    def _clear_flow_state(self, phone: str) -> None:
        self.cache_repository.delete(f"{self.FLOW_KEY_PREFIX}{phone}")
