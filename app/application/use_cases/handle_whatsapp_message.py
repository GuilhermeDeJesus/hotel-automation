"""
Handle WhatsApp Message Use-Case - orchestrates inbound message processing.

This use-case keeps the interface layer thin by centralizing decision logic.
"""

from app.application.dto.checkin_request_dto import CheckinRequestDTO
from app.application.dto.confirm_reservation_request_dto import ConfirmReservationRequestDTO
from app.application.dto.whatsapp_message_request_dto import WhatsAppMessageRequestDTO
from app.application.dto.whatsapp_message_response_dto import WhatsAppMessageResponseDTO
from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
from app.application.use_cases.confirm_reservation import ConfirmReservationUseCase
from app.application.use_cases.conversation import ConversationUseCase
from app.domain.repositories.cache_repository import CacheRepository
from app.domain.repositories.room_repository import RoomRepository


class HandleWhatsAppMessageUseCase:
    """Orchestrates inbound WhatsApp messages and returns a reply."""

    FLOW_KEY_PREFIX = "flow:"
    CONFIRM_RESERVATION_ACTION = "confirm_reservation"

    # Flow steps
    STEP_SUMMARY_DISPLAYED = "summary_displayed"
    STEP_AWAITING_CONFIRMATION = "awaiting_confirmation"
    STEP_AWAITING_EDIT_CHOICE = "awaiting_edit_choice"
    STEP_AWAITING_ROOM_SELECTION = "awaiting_room_selection"

    def __init__(
        self,
        checkin_use_case: CheckInViaWhatsAppUseCase,
        conversation_use_case: ConversationUseCase,
        confirm_reservation_use_case: ConfirmReservationUseCase,
        cache_repository: CacheRepository,
        room_repository: RoomRepository,
    ):
        self.checkin_use_case = checkin_use_case
        self.conversation_use_case = conversation_use_case
        self.confirm_reservation_use_case = confirm_reservation_use_case
        self.cache_repository = cache_repository
        self.room_repository = room_repository

    def execute(self, request_dto: WhatsAppMessageRequestDTO) -> WhatsAppMessageResponseDTO:
        text = (request_dto.message or "").strip()
        content_lower = text.lower()
        phone = request_dto.phone

        flow_state = self._get_flow_state(phone)
        
        # Handle ongoing flows
        if flow_state and flow_state.get("action") == self.CONFIRM_RESERVATION_ACTION:
            return self._handle_confirm_reservation_flow(phone, content_lower, flow_state)

        # Check for new flow intentions
        if self._is_confirm_reservation_intent(content_lower):
            return self._start_confirm_reservation_flow(phone)

        if "check-in" in content_lower or "checkin" in content_lower:
            try:
                response_dto = self.checkin_use_case.execute(
                    CheckinRequestDTO(phone=phone)
                )
                return WhatsAppMessageResponseDTO(reply=response_dto.message, success=True)
            except Exception as exc:
                return WhatsAppMessageResponseDTO(
                    reply=f"Erro ao processar check-in: {exc}",
                    success=False,
                    error=str(exc),
                )

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
            return WhatsAppMessageResponseDTO(reply=ai_reply, success=True)
        except Exception as exc:
            return WhatsAppMessageResponseDTO(
                reply=f"Recebi sua mensagem: '{text}'\n\nComo posso ajudar?",
                success=False,
                error=str(exc),
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

        # Get formatted summary
        reservation = self.confirm_reservation_use_case.reservation_repository.find_by_phone_number(phone)
        formatted_summary = self.confirm_reservation_use_case.get_formatted_summary(reservation)

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

    def _handle_confirm_reservation_flow(
        self, phone: str, content_lower: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Handle ongoing confirmation flow."""
        current_step = flow_state.get("step", self.STEP_SUMMARY_DISPLAYED)

        if current_step == self.STEP_SUMMARY_DISPLAYED:
            return self._handle_summary_response(phone, content_lower, flow_state)

        if current_step == self.STEP_AWAITING_EDIT_CHOICE:
            return self._handle_edit_choice(phone, content_lower, flow_state)

        if current_step == self.STEP_AWAITING_ROOM_SELECTION:
            return self._handle_room_selection(phone, content_lower, flow_state)

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
        self, phone: str, content_lower: str, flow_state: dict
    ) -> WhatsAppMessageResponseDTO:
        """Handle edit choice (QUARTO/DATAS/CANCELAR)."""
        if self._is_negative_confirmation(content_lower) or "cancelar" in content_lower:
            self._clear_flow_state(phone)
            return WhatsAppMessageResponseDTO(
                reply="❌ Edição cancelada. Se precisar de mais algo, me avise.",
                success=True,
            )

        if "quarto" in content_lower:
            reservation = self.confirm_reservation_use_case.reservation_repository.find_by_phone_number(
                phone
            )
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
            return WhatsAppMessageResponseDTO(
                reply="Alteração de datas ainda não está disponível. Cancele e crie uma nova reserva.",
                success=False,
            )

        return WhatsAppMessageResponseDTO(
            reply="Responda: QUARTO / DATAS / CANCELAR",
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

        # Update reservation with new room
        reservation = self.confirm_reservation_use_case.reservation_repository.find_by_phone_number(
            phone
        )
        if reservation:
            reservation.room_number = selected_room
            self.confirm_reservation_use_case.reservation_repository.save(reservation)

        self._clear_flow_state(phone)

        return WhatsAppMessageResponseDTO(
            reply=f"✅ Quarto {selected_room} selecionado. Reserva confirmada!",
            success=True,
        )

    @staticmethod
    def _is_confirm_reservation_intent(content_lower: str) -> bool:
        has_confirm = "confirm" in content_lower
        has_reservation = "reserva" in content_lower or "booking" in content_lower
        return has_confirm and has_reservation

    @staticmethod
    def _is_positive_confirmation(content_lower: str) -> bool:
        return any(
            keyword in content_lower
            for keyword in ["sim", "confirmo", "confirmar", "ok", "yes", "y"]
        )

    @staticmethod
    def _is_negative_confirmation(content_lower: str) -> bool:
        return any(
            keyword in content_lower
            for keyword in ["nao", "não", "cancelar", "cancela", "no", "n"]
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
