"""
Payment Provider - interface para geração de links de pagamento (Fase 1/2).

Permite trocar o provedor (Stripe, Mercado Pago, etc.) sem alterar o orquestrador.
Fase 2: retorna (url, session_id) para permitir criação de Payment e webhook.
"""
from abc import ABC, abstractmethod
from typing import Optional, Tuple


class PaymentProvider(ABC):
    """Interface para provedores de pagamento."""

    @abstractmethod
    def create_checkout_link(
        self,
        reservation_id: str,
        amount_cents: int,
        description: str,
        currency: str = "brl",
        payment_id: Optional[str] = None,
    ) -> Optional[Tuple[str, str]]:
        """
        Cria link de checkout e retorna (url, session_id).

        Args:
            reservation_id: ID da reserva
            amount_cents: Valor em centavos
            description: Descrição da cobrança
            currency: Moeda (brl, usd, etc.)
            payment_id: ID do Payment (Fase 2) para metadata no webhook

        Returns:
            (url, session_id) ou None se não disponível/erro.
        """
        pass
