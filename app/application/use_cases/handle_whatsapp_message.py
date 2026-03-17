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
    STEP_AWAITING_CREATE_CONFIRMATION = "awaiting_create_confirmation"
    STEP_AWAITING_PAYMENT_CHOICE = "awaiting_payment_choice"
    STEP_AWAITING_PAYMENT_PROOF = "awaiting_payment_proof"
    STEP_AWAITING_NEW_CHECKOUT = "awaiting_new_checkout"
    PRE_CHECKIN_ACTION = "pre_checkin"
    STEP_AWAITING_DOCUMENT = "awaiting_document"
    STEP_AWAITING_ARRIVAL_TIME = "awaiting_arrival_time"

    # 6.3 Fallback humano
    FALLBACK_HUMAN_MESSAGE = (
        "Se precisar de atendimento humano, digite ATENDENTE ou ligue para o hotel."
    )

    # Instruções de pagamento (Fase 0 - manual). Configurável via PAYMENT_INSTRUCTIONS.
    DEFAULT_PAYMENT_INSTRUCTIONS = (
        "💳 Pagamento via PIX ou transferência.\n"
        "Chave PIX: contato@hotel.com (ou informe a chave do hotel)\n"
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

    def execute(self, hotel_id: str, request_dto: WhatsAppMessageRequestDTO) -> WhatsAppMessageResponseDTO:
        text = (request_dto.message or "").strip()
        content_lower = text.lower()
        phone = request_dto.phone

        flow_state = self._get_flow_state(f"{hotel_id}:{phone}")
        
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
            return self._start_pre_checkin_flow(phone)

        # 6.6 Resolução de problemas - reportar problema
        if self.support_ticket_use_case and self._is_support_ticket_intent(content_lower):
            return self._handle_support_ticket(phone, text)

        # 6.5 Pedidos durante estadia
        if self.room_order_use_case and self._is_room_order_intent(content_lower):
            return self._handle_room_order(phone, content_lower)

        if "reserva" in content_lower or "booking" in content_lower:
            try:
                ai_reply = self.conversation_use_case.execute(phone, text)
                return WhatsAppMessageResponseDTO(reply=ai_reply, success=True)
            except Exception as exc:
                return WhatsAppMessageResponseDTO(
                    reply="Para fazer uma reserva, envie: RESERVA",
                    success=False,
                    error=str(exc),
                )

        try:
            ai_reply = self.conversation_use_case.execute(phone, text)
            reply = ai_reply
            if self.FALLBACK_HUMAN_MESSAGE and reply:
                reply = f"{reply}\n\n{self.FALLBACK_HUMAN_MESSAGE}"
            return WhatsAppMessageResponseDTO(reply=reply or ai_reply, success=True)
        except Exception as exc:
            return WhatsAppMessageResponseDTO(
                reply=(
                    f"Recebi sua mensagem: '{text}'\n\n"
                    "Como posso ajudar? Você pode fazer reserva, check-in, checkout ou cancelar.\n\n"
                    f"{self.FALLBACK_HUMAN_MESSAGE}"
                ),
                success=False,
                error=str(exc),
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
                "Exemplo: Check-in 15/03/2025 e Check-out 18/03/2025\n"
                "Ou: 15/03/2025 a 18/03/2025"
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
        if self._is_negative_confirmation(content_lower) or "cancelar" in content_lower:
            self._clear_flow_state(f"{hotel_id}:{phone}")
            return WhatsAppMessageResponseDTO(
                reply="❌ Reserva cancelada. Se precisar de algo mais, me avise.",
                success=True,
            )

        step = flow_state.get("step", self.STEP_AWAITING_DATES)

        if step == self.STEP_AWAITING_DATES:
            return self._handle_create_awaiting_dates(hotel_id, phone, text, flow_state)

        if step == self.STEP_AWAITING_ROOM_CHOICE:
            return self._handle_create_awaiting_room_choice(hotel_id, phone, content_lower, flow_state)

        if step == self.STEP_AWAITING_NAME:
            return self._handle_create_awaiting_name(hotel_id, phone, text, flow_state)

        if step == self.STEP_AWAITING_PAYMENT_CHOICE:
            return self._handle_create_awaiting_payment_choice(hotel_id, phone, content_lower, flow_state)

        if step == self.STEP_AWAITING_PAYMENT_PROOF:
            return self._handle_create_awaiting_payment_proof(
                hotel_id, phone, text, flow_state, has_media=has_media
            )

        return WhatsAppMessageResponseDTO(
            reply="Desculpe, ocorreu um erro no fluxo. Tente novamente.",
            success=False,
        )

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
            {"number": r.number, "room_type": r.room_type, "daily_rate": r.daily_rate}
            for r in available
        ]
        self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)

        room_list = "\n".join(
            f"- {r.number} ({r.room_type}) - R$ {r.daily_rate:.2f}/noite"
            for r in available
        )
        return WhatsAppMessageResponseDTO(
            reply=f"Quartos disponíveis:\n\n{room_list}\n\nQual você escolhe? (informe o número)",
            success=True,
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
        """Process guest name input, create reservation PENDING, and show payment choice."""
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
            self._clear_flow_state(phone)
            return WhatsAppMessageResponseDTO(
                reply=response.message,
                success=False,
            )

        num_nights = (check_out - check_in).days
        total = room["daily_rate"] * num_nights
        summary_lines = [
            f"📋 Resumo da reserva:",
            f"- Nome: {name}",
            f"- Check-in: {check_in.strftime('%d/%m/%Y')}",
            f"- Check-out: {check_out.strftime('%d/%m/%Y')}",
            f"- Quarto: {room_number} ({room['room_type']})",
            f"- Total: R$ {total:.2f}",
            "",
        ]

        requires_payment, allows_without = self._get_payment_config()

        if requires_payment:
            payment_msg, is_manual = self._build_payment_message(
                response.reservation_id, total, name, room_number
            )
            summary_lines.append(payment_msg)
            if is_manual:
                flow_state["step"] = self.STEP_AWAITING_PAYMENT_PROOF
                flow_state["guest_name"] = name
                flow_state["reservation_id"] = response.reservation_id
                flow_state["selected_room"] = room_number
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
        flow_state["guest_name"] = name
        flow_state["reservation_id"] = response.reservation_id
        self._set_flow_state(f"{hotel_id}:{phone}", flow_state, ttl_seconds=900)

        if allows_without:
            summary_lines.append("Como deseja prosseguir?")
            summary_lines.append("1. Confirmar e pagar agora")
            summary_lines.append("2. Confirmar sem pagamento imediato")
        else:
            summary_lines.append("Para confirmar, efetue o pagamento.")
            summary_lines.append("Responda 1 para ver instruções de pagamento.")

        return WhatsAppMessageResponseDTO(
            reply="\n".join(summary_lines),
            success=True,
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

        _, allows_without = self._get_payment_config()

        # Opção 1: Pagar agora (Fase 0 ou Fase 1 - link)
        if self._is_pay_now_choice(content_lower):
            reservation_id = flow_state.get("reservation_id", "")
            guest_name = flow_state.get("guest_name", "Reserva")
            room_number = flow_state.get("selected_room", "")
            reservation = self.reservation_repository.find_by_phone_number(phone, hotel_id)
            total = reservation.total_amount if reservation else 0.0
            payment_msg, is_manual = self._build_payment_message(
                reservation_id, total, guest_name, room_number
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
                reply=(
                    "Responda:\n"
                    "1 - Confirmar e pagar agora\n"
                    "2 - Confirmar sem pagamento imediato"
                ),
                success=True,
            )
        return WhatsAppMessageResponseDTO(
            reply=(
                "Para confirmar sua reserva, efetue o pagamento. "
                "Responda 1 para ver as instruções."
            ),
            success=True,
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
            self._clear_flow_state(phone)
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

    def _get_payment_config(self) -> tuple[bool, bool]:
        """
        Retorna (requires_payment_for_confirmation, allows_reservation_without_payment).
        Se não houver hotel configurado, usa defaults: (False, True) = oferece ambas opções.
        """
        hotel = self.hotel_repository.get_active_hotel()
        if not hotel:
            return False, True
        return (
            getattr(hotel, "requires_payment_for_confirmation", False),
            getattr(hotel, "allows_reservation_without_payment", True),
        )

    def _build_payment_message(
        self,
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
                amount=total,
                status="PENDING",
                payment_method="stripe",
                transaction_id=session_id,
            )
            self.payment_repository.save(payment)
            return (
                "Para confirmar sua reserva, efetue o pagamento:\n\n"
                f"🔗 {url}\n\n"
                "Sua reserva será confirmada após a confirmação do pagamento.",
                False,
            )
        instructions = self._get_payment_instructions()
        return (
            "Para confirmar sua reserva, efetue o pagamento:\n\n"
            f"{instructions}\n\n"
            "Sua reserva será confirmada após a confirmação do pagamento.",
            True,
        )

    def _get_payment_instructions(self) -> str:
        """Retorna instruções de pagamento (Fase 0: manual)."""
        import os
        return os.getenv("PAYMENT_INSTRUCTIONS", self.DEFAULT_PAYMENT_INSTRUCTIONS)

    # --- 6.1 Pré-check-in ---
    @staticmethod
    def _is_pre_checkin_intent(content_lower: str) -> bool:
        return any(
            kw in content_lower
            for kw in ["pré-checkin", "pre checkin", "precheckin", "documentos", "registrar cpf"]
        )

    def _start_pre_checkin_flow(self, phone: str) -> WhatsAppMessageResponseDTO:
        reservation = self.reservation_repository.find_by_phone_number(phone)
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

    def _start_cancel_reservation_flow(self, phone: str) -> WhatsAppMessageResponseDTO:
        """Initiate reservation cancellation flow."""
        response = self.cancel_reservation_use_case.prepare_cancellation(
            CancelReservationRequestDTO(phone=phone)
        )

        if not response.success:
            return WhatsAppMessageResponseDTO(reply=response.message, success=False)

        if not response.can_cancel:
            return WhatsAppMessageResponseDTO(reply=response.message, success=True)

        flow_state = {
            "action": self.CANCEL_RESERVATION_ACTION,
            "step": self.STEP_SUMMARY_DISPLAYED,
        }
        self._set_flow_state(phone, flow_state, ttl_seconds=900)

        reply_parts = [
            response.summary or "Resumo da reserva",
            "\nDeseja realmente cancelar? Responda: SIM ou NÃO",
        ]

        return WhatsAppMessageResponseDTO(
            reply="\n".join(reply_parts),
            success=True,
        )

    def _handle_cancel_reservation_flow(
        self, phone: str, content_lower: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Handle ongoing cancellation flow."""
        if self._is_negative_confirmation(content_lower):
            self._clear_flow_state(phone)
            return WhatsAppMessageResponseDTO(
                reply="Operação cancelada. Sua reserva permanece ativa.",
                success=True,
            )

        if self._is_positive_confirmation(content_lower):
            self._clear_flow_state(phone)
            response = self.cancel_reservation_use_case.cancel(
                CancelReservationRequestDTO(phone=phone)
            )
            return WhatsAppMessageResponseDTO(
                reply=f"✅ {response.message}",
                success=response.success,
            )

        return WhatsAppMessageResponseDTO(
            reply="Responda com SIM para cancelar ou NÃO para manter a reserva.",
            success=True,
        )

    def _start_confirm_reservation_flow(self, phone: str) -> WhatsAppMessageResponseDTO:
        """Initiate reservation confirmation flow."""
        response = self.confirm_reservation_use_case.prepare_confirmation(
            ConfirmReservationRequestDTO(phone=phone)
        )

        if not response.success:
            return WhatsAppMessageResponseDTO(reply=response.message, success=False)

        if not response.can_confirm:
            return WhatsAppMessageResponseDTO(reply=response.message, success=True)

        # Get formatted summary via use case (encapsula acesso ao repositório)
        formatted_summary = self.confirm_reservation_use_case.get_formatted_summary_for_phone(phone)
        if not formatted_summary:
            formatted_summary = response.summary or "Resumo da reserva"

        flow_state = {
            "action": self.CONFIRM_RESERVATION_ACTION,
            "step": self.STEP_SUMMARY_DISPLAYED,
        }
        self._set_flow_state(phone, flow_state, ttl_seconds=900)

        reply_parts = [
            formatted_summary,
            "\nTudo está correto?",
            "Responda: SIM / NÃO / EDITAR",
        ]

        return WhatsAppMessageResponseDTO(
            reply="\n".join(reply_parts),
            success=True,
        )

    def _start_extend_reservation_flow(self, phone: str) -> WhatsAppMessageResponseDTO:
        """Initiate reservation extension flow."""
        response = self.extend_reservation_use_case.prepare_extension(
            ExtendReservationRequestDTO(phone=phone)
        )

        if not response.success:
            return WhatsAppMessageResponseDTO(reply=response.message, success=False)

        if not response.can_extend:
            return WhatsAppMessageResponseDTO(reply=response.message, success=True)

        flow_state = {
            "action": self.EXTEND_RESERVATION_ACTION,
            "step": self.STEP_AWAITING_NEW_CHECKOUT,
        }
        self._set_flow_state(phone, flow_state, ttl_seconds=900)

        reply_parts = [
            response.summary or "Resumo da reserva",
            "\n📅 " + response.message,
        ]

        return WhatsAppMessageResponseDTO(
            reply="\n".join(reply_parts),
            success=True,
        )

    def _handle_extend_reservation_flow(
        self, phone: str, text: str, content_lower: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Handle ongoing extension flow."""
        if self._is_negative_confirmation(content_lower) or "cancelar" in content_lower:
            self._clear_flow_state(phone)
            return WhatsAppMessageResponseDTO(
                reply="Operação cancelada. Sua reserva permanece como estava.",
                success=True,
            )

        current_step = flow_state.get("step", self.STEP_AWAITING_NEW_CHECKOUT)
        if current_step == self.STEP_AWAITING_NEW_CHECKOUT:
            return self._handle_extend_awaiting_new_checkout(phone, text, flow_state)

        return WhatsAppMessageResponseDTO(
            reply="Desculpe, ocorreu um erro no fluxo. Tente novamente.",
            success=False,
        )

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
        self, phone: str, text: str, flow_state: dict
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
            ExtendReservationRequestDTO(phone=phone, new_checkout=new_checkout)
        )

        self._clear_flow_state(phone)

        return WhatsAppMessageResponseDTO(
            reply=response.message,
            success=response.success,
        )

    def _handle_confirm_reservation_flow(
        self, phone: str, text: str, content_lower: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Handle ongoing confirmation flow."""
        current_step = flow_state.get("step", self.STEP_SUMMARY_DISPLAYED)

        if current_step == self.STEP_SUMMARY_DISPLAYED:
            return self._handle_summary_response(phone, content_lower, flow_state)

        if current_step == self.STEP_AWAITING_EDIT_CHOICE:
            return self._handle_edit_choice(phone, text, content_lower, flow_state)

        if current_step == self.STEP_AWAITING_ROOM_SELECTION:
            return self._handle_room_selection(phone, content_lower, flow_state)

        if current_step == self.STEP_AWAITING_NEW_DATES:
            return self._handle_awaiting_new_dates(phone, text, flow_state)

        return WhatsAppMessageResponseDTO(
            reply="Desculpe, ocorreu um erro no fluxo. Tente novamente.",
            success=False,
        )

    def _handle_summary_response(
        self, phone: str, content_lower: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Handle response to summary (SIM/NÃO/EDITAR)."""
        if self._is_negative_confirmation(content_lower):
            self._clear_flow_state(phone)
            return WhatsAppMessageResponseDTO(
                reply="❌ Cancelado. Se precisar de algo mais, me avise.",
                success=True,
            )

        if self._is_positive_confirmation(content_lower):
            self._clear_flow_state(phone)
            response = self.confirm_reservation_use_case.confirm(
                ConfirmReservationRequestDTO(phone=phone)
            )
            return WhatsAppMessageResponseDTO(
                reply=f"✅ {response.message}",
                success=response.success,
            )

        if self._is_edit_request(content_lower):
            flow_state["step"] = self.STEP_AWAITING_EDIT_CHOICE
            self._set_flow_state(phone, flow_state, ttl_seconds=900)
            return WhatsAppMessageResponseDTO(
                reply="O que deseja alterar?\n\nResponda: QUARTO / DATAS / CANCELAR",
                success=True,
            )

        return WhatsAppMessageResponseDTO(
            reply="Responda com SIM para confirmar, NÃO para cancelar ou EDITAR para alterar.",
            success=True,
        )

    def _handle_edit_choice(
        self, phone: str, text: str, content_lower: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Handle edit choice (QUARTO/DATAS/CANCELAR)."""
        if self._is_negative_confirmation(content_lower) or "cancelar" in content_lower:
            self._clear_flow_state(phone)
            return WhatsAppMessageResponseDTO(
                reply="❌ Edição cancelada. Se precisar de mais algo, me avise.",
                success=True,
            )

        if "quarto" in content_lower:
            reservation = self.reservation_repository.find_by_phone_number(phone)
            if not reservation or not reservation.stay_period:
                self._clear_flow_state(phone)
                return WhatsAppMessageResponseDTO(
                    reply="Não consegui localizar os dados da reserva.",
                    success=False,
                )

            available_rooms = self.room_repository.find_available(
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
            self._set_flow_state(phone, flow_state, ttl_seconds=900)

            room_list = "\n".join(
                [
                    f"- {room.number} ({room.room_type}) - R$ {room.daily_rate:.2f}/noite"
                    for room in available_rooms
                ]
            )
            reply = f"Quartos disponíveis:\n\n{room_list}\n\nQual você escolhe?"
            return WhatsAppMessageResponseDTO(reply=reply, success=True)

        if "data" in content_lower or "datas" in content_lower:
            reservation = self.reservation_repository.find_by_phone_number(phone)
            if not reservation or not reservation.stay_period or not reservation.room_number:
                self._clear_flow_state(phone)
                return WhatsAppMessageResponseDTO(
                    reply="Não consegui localizar os dados da reserva.",
                    success=False,
                )

            flow_state["step"] = self.STEP_AWAITING_NEW_DATES
            self._set_flow_state(phone, flow_state, ttl_seconds=900)
            return WhatsAppMessageResponseDTO(
                reply=(
                    "📅 Informe as novas datas da estadia.\n\n"
                    "Exemplo: 20/04/2025 e 23/04/2025\n"
                    "Ou: 20/04/2025 a 23/04/2025"
                ),
                success=True,
            )

        return WhatsAppMessageResponseDTO(
            reply="Responda: QUARTO / DATAS / CANCELAR",
            success=True,
        )

    def _handle_awaiting_new_dates(
        self, phone: str, text: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Process new dates input in edit flow."""
        reservation = self.reservation_repository.find_by_phone_number(phone)
        if not reservation or not reservation.stay_period or not reservation.room_number:
            self._clear_flow_state(phone)
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
            reservation.room_number,
            check_in,
            check_out,
            exclude_reservation_id=reservation.id,
        ):
            return WhatsAppMessageResponseDTO(
                reply=f"O quarto {reservation.room_number} não está disponível para este período. Tente outras datas.",
                success=False,
            )

        room = self.room_repository.get_by_number(reservation.room_number)
        if not room:
            self._clear_flow_state(phone)
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
            self.reservation_repository.save(reservation)
        except exceptions.InvalidDatesChangeState as e:
            return WhatsAppMessageResponseDTO(
                reply=str(e),
                success=False,
            )

        # Volta ao resumo para nova confirmação
        flow_state["step"] = self.STEP_SUMMARY_DISPLAYED
        self._set_flow_state(phone, flow_state, ttl_seconds=900)

        formatted_summary = self.confirm_reservation_use_case.get_formatted_summary_for_phone(phone)
        reply_parts = [
            formatted_summary or "Resumo atualizado:",
            "\n✅ Datas alteradas com sucesso!",
            "\nTudo está correto agora?",
            "Responda: SIM / NÃO / EDITAR",
        ]
        return WhatsAppMessageResponseDTO(
            reply="\n".join(reply_parts),
            success=True,
        )

    def _handle_room_selection(
        self, phone: str, content_lower: str, flow_state: dict
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

        reservation = self.reservation_repository.find_by_phone_number(phone)
        if not reservation:
            self._clear_flow_state(phone)
            return WhatsAppMessageResponseDTO(
                reply="Não consegui localizar os dados da reserva.",
                success=False,
            )

        if not reservation.stay_period:
            self._clear_flow_state(phone)
            return WhatsAppMessageResponseDTO(
                reply="Não consegui localizar os dados da reserva.",
                success=False,
            )

        # Validar disponibilidade antes de chamar domínio
        if not self.room_repository.is_available(
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
            self.reservation_repository.save(reservation)
        except exceptions.InvalidRoomChangeState as e:
            return WhatsAppMessageResponseDTO(
                reply=str(e),
                success=False,
            )

        self._clear_flow_state(phone)

        return WhatsAppMessageResponseDTO(
            reply=f"✅ Quarto {selected_room} selecionado. Reserva confirmada!",
            success=True,
        )

    @staticmethod
    def _is_cancel_reservation_intent(content_lower: str) -> bool:
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
