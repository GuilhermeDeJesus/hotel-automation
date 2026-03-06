"""
Payment Webhook - Fase 2.

Recebe eventos do Stripe (checkout.session.completed, checkout.session.expired).
"""
import os
import logging

from fastapi import APIRouter, Request, Response, Depends

from app.application.use_cases.handle_payment_webhook import HandlePaymentWebhookUseCase
from app.interfaces.dependencies import get_payment_webhook_use_case

router = APIRouter(prefix="/webhook", tags=["payment"])
logger = logging.getLogger(__name__)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    use_case: HandlePaymentWebhookUseCase = Depends(get_payment_webhook_use_case),
) -> Response:
    """
    Webhook Stripe - processa checkout.session.completed e checkout.session.expired.

    Requer STRIPE_WEBHOOK_SECRET para verificar assinatura.
    """
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if not webhook_secret:
        logger.warning("STRIPE_WEBHOOK_SECRET não configurado")
        return Response(status_code=500, content="Webhook não configurado")

    result = use_case.handle_stripe_event(payload, sig_header, webhook_secret)

    if result.processed:
        logger.info(f"Webhook processado: {result.message}")
        return Response(status_code=200, content="OK")

    logger.warning(f"Webhook não processado: {result.message}")
    return Response(status_code=400, content=result.message)
