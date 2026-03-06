"""
Handle Payment Webhook Use Case - Fase 2.

Processa webhooks do provedor de pagamento (Stripe).
- Marca Payment como APPROVED/REJECTED/EXPIRED
- Regra: Payment.APPROVED → reservation.confirm()
"""
from dataclasses import dataclass
from typing import Optional

from app.domain.entities.payment.payment import Payment
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.repositories.payment_repository import PaymentRepository
from app.domain.repositories.reservation_repository import ReservationRepository


@dataclass
class PaymentWebhookResult:
    """Resultado do processamento do webhook."""
    processed: bool
    payment_id: Optional[str] = None
    reservation_confirmed: bool = False
    message: str = ""


class HandlePaymentWebhookUseCase:
    """
    Processa eventos de webhook do provedor de pagamento.

    Regras:
    - checkout.session.completed (Stripe) → Payment.APPROVED → reservation.confirm()
    - checkout.session.expired → Payment.EXPIRED
    - payment_intent.payment_failed → Payment.REJECTED
    """

    def __init__(
        self,
        payment_repository: PaymentRepository,
        reservation_repository: ReservationRepository,
    ):
        self.payment_repository = payment_repository
        self.reservation_repository = reservation_repository

    def handle_stripe_event(self, payload: bytes, sig_header: str, webhook_secret: str) -> PaymentWebhookResult:
        """
        Processa evento Stripe (verifica assinatura e despacha).

        Args:
            payload: corpo raw do request
            sig_header: header Stripe-Signature
            webhook_secret: STRIPE_WEBHOOK_SECRET

        Returns:
            PaymentWebhookResult com status do processamento
        """
        try:
            import stripe

            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except ValueError as e:
            return PaymentWebhookResult(processed=False, message=f"Payload inválido: {e}")
        except Exception as e:
            return PaymentWebhookResult(processed=False, message=f"Erro na verificação: {e}")

        if event["type"] == "checkout.session.completed":
            return self._handle_checkout_completed(event["data"]["object"])
        if event["type"] == "checkout.session.expired":
            return self._handle_checkout_expired(event["data"]["object"])

        return PaymentWebhookResult(processed=True, message=f"Evento {event['type']} ignorado")

    def _handle_checkout_completed(self, session: dict) -> PaymentWebhookResult:
        """checkout.session.completed → Payment.APPROVED → reservation.confirm()."""
        payment_id = session.get("metadata", {}).get("payment_id")
        if not payment_id:
            return PaymentWebhookResult(
                processed=False,
                message="metadata.payment_id ausente",
            )

        payment = self.payment_repository.find_by_id(payment_id)
        if not payment:
            return PaymentWebhookResult(
                processed=False,
                payment_id=payment_id,
                message="Payment não encontrado",
            )

        if payment.is_approved():
            return PaymentWebhookResult(
                processed=True,
                payment_id=payment_id,
                reservation_confirmed=True,
                message="Pagamento já estava aprovado",
            )

        try:
            payment.approve(transaction_id=session.get("id"))
            self.payment_repository.save(payment)
        except Exception as e:
            return PaymentWebhookResult(
                processed=False,
                payment_id=payment_id,
                message=str(e),
            )

        reservation = self.reservation_repository.find_by_id(payment.reservation_id)
        if reservation and reservation.status == ReservationStatus.PENDING:
            reservation.confirm()
            self.reservation_repository.save(reservation)
            return PaymentWebhookResult(
                processed=True,
                payment_id=payment_id,
                reservation_confirmed=True,
                message="Pagamento aprovado e reserva confirmada",
            )

        return PaymentWebhookResult(
            processed=True,
            payment_id=payment_id,
            reservation_confirmed=False,
            message="Pagamento aprovado",
        )

    def _handle_checkout_expired(self, session: dict) -> PaymentWebhookResult:
        """checkout.session.expired → Payment.EXPIRED."""
        payment_id = session.get("metadata", {}).get("payment_id")
        if not payment_id:
            return PaymentWebhookResult(
                processed=True,
                message="metadata.payment_id ausente, evento ignorado",
            )

        payment = self.payment_repository.find_by_id(payment_id)
        if not payment:
            return PaymentWebhookResult(
                processed=True,
                payment_id=payment_id,
                message="Payment não encontrado",
            )

        if payment.is_pending():
            payment.expire()
            self.payment_repository.save(payment)

        return PaymentWebhookResult(
            processed=True,
            payment_id=payment_id,
            message="Pagamento marcado como expirado",
        )
