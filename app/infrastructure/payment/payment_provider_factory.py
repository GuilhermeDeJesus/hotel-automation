"""
Factory para PaymentProvider - escolhe provedor conforme configuração.
"""
import os

from app.domain.services.payment_provider import PaymentProvider
from app.infrastructure.payment.manual_payment_provider import ManualPaymentProvider
from app.infrastructure.payment.stripe_payment_provider import StripePaymentProvider


def get_payment_provider() -> PaymentProvider:
    """
    Retorna o provedor de pagamento conforme PAYMENT_PROVIDER.

    - stripe: usa Stripe (requer STRIPE_SECRET_KEY)
    - manual ou vazio: instruções manuais (Fase 0)
    """
    provider = (os.getenv("PAYMENT_PROVIDER") or "manual").lower().strip()
    if provider == "stripe" and os.getenv("STRIPE_SECRET_KEY"):
        return StripePaymentProvider()
    return ManualPaymentProvider()
