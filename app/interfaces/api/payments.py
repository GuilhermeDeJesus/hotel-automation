"""Payments API - list and manage payments."""
import logging
from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.use_cases.confirm_payment_manual import ConfirmPaymentManualUseCase
from app.application.use_cases.list_payments import ListPaymentsUseCase
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.payment_repository_sql import PaymentRepositorySQL
from app.infrastructure.persistence.sql.reservation_repository_sql import ReservationRepositorySQL

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/saas/payments", tags=["payments"])

CONFIRMATION_MESSAGE = (
    "✅ Sua reserva foi confirmada!\n\n"
    "Te esperamos no check-in. Se precisar de algo antes da chegada, "
    "como pré-check-in ou pedidos de quarto, é só nos avisar aqui."
)


def get_list_payments_use_case() -> Generator[ListPaymentsUseCase, None, None]:
    session = SessionLocal()
    try:
        repo = PaymentRepositorySQL(session)
        yield ListPaymentsUseCase(payment_repository=repo)
    finally:
        session.close()


def get_confirm_payment_use_case() -> Generator[ConfirmPaymentManualUseCase, None, None]:
    session = SessionLocal()
    try:
        payment_repo = PaymentRepositorySQL(session)
        reservation_repo = ReservationRepositorySQL(session)
        yield ConfirmPaymentManualUseCase(
            payment_repository=payment_repo,
            reservation_repository=reservation_repo,
        )
    finally:
        session.close()


@router.get("")
def list_payments(
    reservation_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    use_case: ListPaymentsUseCase = Depends(get_list_payments_use_case),
):
    """List payments with optional filters."""
    items = use_case.execute(
        reservation_id=reservation_id,
        status=status,
        limit=limit,
    )
    return {"items": items}


def _normalize_phone(phone: str) -> str:
    """Retorna apenas dígitos do número."""
    if not phone:
        return ""
    return "".join(ch for ch in str(phone) if ch.isdigit())


def _send_whatsapp_confirmation(phone: str) -> bool:
    """Envia mensagem de confirmação via WhatsApp. Retorna True se enviou com sucesso."""
    phone = _normalize_phone(phone)
    if not phone or len(phone) < 10:
        return False
    try:
        from app.interfaces.api.whatsapp_webhook import (
            whatsapp_client,
            whatsapp_twilio_client,
        )
        # Tenta Twilio primeiro, depois Meta
        if whatsapp_twilio_client:
            r = whatsapp_twilio_client.send_text_message(phone, CONFIRMATION_MESSAGE)
            if r.get("success"):
                logger.info(f"📱 Confirmação enviada via Twilio para {phone}")
                return True
        if whatsapp_client:
            r = whatsapp_client.send_text_message(phone, CONFIRMATION_MESSAGE)
            if r.get("success"):
                logger.info(f"📱 Confirmação enviada via Meta para {phone}")
                return True
    except Exception as exc:
        logger.warning(f"⚠️ Falha ao enviar confirmação WhatsApp: {exc}")
    return False


@router.post("/{payment_id}/confirm")
def confirm_payment(
    payment_id: str,
    transaction_id: str | None = Query(default=None),
    use_case: ConfirmPaymentManualUseCase = Depends(get_confirm_payment_use_case),
):
    """Confirm payment manually (Fase 0 - comprovante recebido)."""
    result = use_case.execute(payment_id, transaction_id=transaction_id)
    if result["success"]:
        guest_phone = result.get("guest_phone")
        if guest_phone:
            _send_whatsapp_confirmation(guest_phone)
        return result
    raise HTTPException(status_code=400, detail=result["error"])
