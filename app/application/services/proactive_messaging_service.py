"""
Proactive Messaging Service - 6.2 Comunicação proativa.

Envia mensagens automáticas em momentos-chave:
- 24h antes: lembrete da reserva
- No dia do check-in: "Hoje é o dia!"
- 1 dia antes do checkout: oferta de extensão
- Pós-checkout: feedback
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Optional


@dataclass
class ProactiveMessage:
    phone: str
    message_type: str
    message: str
    reservation_id: str


class ProactiveMessageSender(ABC):
    """Interface para envio de mensagens (WhatsApp)."""

    @abstractmethod
    def send(self, phone: str, message: str) -> bool:
        pass


class ProactiveMessageLogRepository(ABC):
    """Interface para log de mensagens enviadas."""

    @abstractmethod
    def was_sent(self, reservation_id: str, message_type: str, reference_date: date) -> bool:
        pass

    @abstractmethod
    def log_sent(self, reservation_id: str, message_type: str) -> None:
        pass


class ProactiveMessagingService:
    """6.2 Gera mensagens proativas conforme calendário de reservas."""

    MSG_24H_BEFORE = (
        "📅 Sua reserva é amanhã!\n\n"
        "Check-in a partir das 14h. Quando chegar, responda 'cheguei' para finalizar.\n"
        "Quer fazer o pré-check-in? Responda PRÉ-CHECKIN para registrar seus documentos."
    )
    MSG_DAY_OF_CHECKIN = (
        "🎉 Hoje é o dia da sua reserva!\n\n"
        "Quando chegar no hotel, responda 'cheguei' para fazer o check-in."
    )
    MSG_1D_BEFORE_CHECKOUT = (
        "📋 Checkout amanhã às 12h.\n\n"
        "Quer estender a estadia? Responda 'estender' para mais dias."
    )
    MSG_POST_CHECKOUT = (
        "Obrigado pela estadia! 🙏\n\n"
        "Como foi sua experiência? Responda de 1 a 5 (5 = excelente)."
    )

    def __init__(
        self,
        reservation_repository,
        log_repository: ProactiveMessageLogRepository,
        sender: Optional[ProactiveMessageSender] = None,
    ):
        self.reservation_repository = reservation_repository
        self.log_repository = log_repository
        self.sender = sender

    def get_messages_to_send(self, reference_date: date) -> List[ProactiveMessage]:
        """Retorna lista de mensagens a enviar na data de referência."""
        messages = []
        # Reservas com check-in em reference_date + 1 (24h antes)
        # Reservas com check-in em reference_date (dia do check-in)
        # Reservas com check-out em reference_date + 1 (1 dia antes do checkout)
        # Reservas com check-out em reference_date (pós-checkout)

        # Buscar reservas - precisamos de método no repository
        if hasattr(self.reservation_repository, "find_for_proactive_messaging"):
            reservations = self.reservation_repository.find_for_proactive_messaging(reference_date)
        else:
            reservations = []

        for res in reservations:
            if not res.stay_period:
                continue
            phone = str(res.guest_phone)
            rid = res.id

            # 24h antes do check-in
            if res.stay_period.start == reference_date + timedelta(days=1):
                if not self.log_repository.was_sent(rid, "24h_before", reference_date):
                    messages.append(ProactiveMessage(
                        phone=phone,
                        message_type="24h_before",
                        message=self.MSG_24H_BEFORE,
                        reservation_id=rid,
                    ))

            # Dia do check-in
            if res.stay_period.start == reference_date:
                if not self.log_repository.was_sent(rid, "day_of_checkin", reference_date):
                    messages.append(ProactiveMessage(
                        phone=phone,
                        message_type="day_of_checkin",
                        message=self.MSG_DAY_OF_CHECKIN,
                        reservation_id=rid,
                    ))

            # 1 dia antes do checkout
            if res.stay_period.end == reference_date + timedelta(days=1):
                if res.status.name == "CHECKED_IN":
                    if not self.log_repository.was_sent(rid, "1d_before_checkout", reference_date):
                        messages.append(ProactiveMessage(
                            phone=phone,
                            message_type="1d_before_checkout",
                            message=self.MSG_1D_BEFORE_CHECKOUT,
                            reservation_id=rid,
                        ))

            # Pós-checkout
            if res.stay_period.end == reference_date and res.status.name == "CHECKED_OUT":
                if not self.log_repository.was_sent(rid, "post_checkout", reference_date):
                    messages.append(ProactiveMessage(
                        phone=phone,
                        message_type="post_checkout",
                        message=self.MSG_POST_CHECKOUT,
                        reservation_id=rid,
                    ))

        return messages
