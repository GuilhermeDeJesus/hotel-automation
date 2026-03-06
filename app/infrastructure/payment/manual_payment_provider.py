"""
Manual Payment Provider - Fase 0, sem link.

Retorna None para que o orquestrador use instruções manuais (PIX, TED, etc.).
"""
from typing import Optional, Tuple

from app.domain.services.payment_provider import PaymentProvider


class ManualPaymentProvider(PaymentProvider):
    """Provider que não gera link - fallback para Fase 0."""

    def create_checkout_link(
        self,
        reservation_id: str,
        amount_cents: int,
        description: str,
        currency: str = "brl",
        payment_id: Optional[str] = None,
    ) -> Optional[Tuple[str, str]]:
        return None
