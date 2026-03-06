"""
Stripe Payment Provider - Fase 1/2, gera link de checkout.

Requer STRIPE_SECRET_KEY. Cria sessão de checkout e retorna (url, session_id).
Fase 2: metadata inclui payment_id para webhook.
"""
import os
from typing import Optional, Tuple

from app.domain.services.payment_provider import PaymentProvider


class StripePaymentProvider(PaymentProvider):
    """Gera link de pagamento via Stripe Checkout."""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ):
        self.secret_key = secret_key or os.getenv("STRIPE_SECRET_KEY")
        self.success_url = success_url or os.getenv(
            "STRIPE_SUCCESS_URL", "https://example.com/payment/success"
        )
        self.cancel_url = cancel_url or os.getenv(
            "STRIPE_CANCEL_URL", "https://example.com/payment/cancel"
        )

    def create_checkout_link(
        self,
        reservation_id: str,
        amount_cents: int,
        description: str,
        currency: str = "brl",
        payment_id: Optional[str] = None,
    ) -> Optional[Tuple[str, str]]:
        if not self.secret_key:
            return None

        try:
            import stripe

            stripe.api_key = self.secret_key

            metadata = {"reservation_id": reservation_id}
            if payment_id:
                metadata["payment_id"] = payment_id

            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[
                    {
                        "price_data": {
                            "currency": currency,
                            "product_data": {
                                "name": f"Reserva #{reservation_id[:8]}",
                                "description": description[:500],
                            },
                            "unit_amount": amount_cents,
                        },
                        "quantity": 1,
                    }
                ],
                success_url=f"{self.success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=self.cancel_url,
                metadata=metadata,
            )
            return (session.url, session.id)
        except Exception:
            return None
