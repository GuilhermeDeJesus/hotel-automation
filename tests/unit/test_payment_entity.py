"""Testes unitários da entidade Payment."""
import pytest
from datetime import datetime

from app.domain.entities.payment.payment import Payment
from app.domain import exceptions


def test_payment_approve_success():
    """Aprovar pagamento PENDING deve funcionar."""
    payment = Payment(
        payment_id="pay-1",
        reservation_id="res-1",
        amount=100.0,
        status="PENDING",
    )
    payment.approve(transaction_id="tx-123")
    assert payment.status == "APPROVED"
    assert payment.transaction_id == "tx-123"
    assert payment.approved_at is not None


def test_payment_approve_already_approved_raises():
    """Aprovar pagamento já aprovado deve lançar InvalidPaymentState."""
    payment = Payment(
        payment_id="pay-1",
        reservation_id="res-1",
        amount=100.0,
        status="APPROVED",
    )
    with pytest.raises(exceptions.InvalidPaymentState):
        payment.approve()


def test_payment_reject_pending():
    """Rejeitar pagamento PENDING deve funcionar."""
    payment = Payment(
        payment_id="pay-1",
        reservation_id="res-1",
        amount=100.0,
        status="PENDING",
    )
    payment.reject()
    assert payment.status == "REJECTED"


def test_payment_expire_pending():
    """Expirar pagamento PENDING deve funcionar."""
    payment = Payment(
        payment_id="pay-1",
        reservation_id="res-1",
        amount=100.0,
        status="PENDING",
    )
    payment.expire()
    assert payment.status == "EXPIRED"


def test_payment_refund_approved():
    """Estornar pagamento APPROVED deve funcionar."""
    payment = Payment(
        payment_id="pay-1",
        reservation_id="res-1",
        amount=100.0,
        status="APPROVED",
    )
    payment.refund()
    assert payment.status == "REFUNDED"


def test_payment_refund_pending_raises():
    """Estornar pagamento PENDING deve lançar InvalidPaymentState."""
    payment = Payment(
        payment_id="pay-1",
        reservation_id="res-1",
        amount=100.0,
        status="PENDING",
    )
    with pytest.raises(exceptions.InvalidPaymentState):
        payment.refund()


def test_payment_is_approved():
    """is_approved retorna True apenas para APPROVED."""
    assert Payment("1", "r1", 10.0, "APPROVED").is_approved() is True
    assert Payment("1", "r1", 10.0, "PENDING").is_approved() is False


def test_payment_is_pending():
    """is_pending retorna True apenas para PENDING."""
    assert Payment("1", "r1", 10.0, "PENDING").is_pending() is True
    assert Payment("1", "r1", 10.0, "APPROVED").is_pending() is False
