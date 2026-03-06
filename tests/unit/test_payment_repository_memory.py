"""Testes unitários do PaymentRepositoryMemory."""
import pytest

from app.domain.entities.payment.payment import Payment
from app.infrastructure.persistence.memory.payment_repository_memory import PaymentRepositoryMemory


def test_save_and_find_by_id():
    """Salvar e buscar por ID."""
    repo = PaymentRepositoryMemory()
    payment = Payment(
        payment_id="pay-1",
        reservation_id="res-1",
        amount=150.0,
        status="PENDING",
    )
    repo.save(payment)
    found = repo.find_by_id("pay-1")
    assert found is not None
    assert found.id == "pay-1"
    assert found.reservation_id == "res-1"
    assert found.amount == 150.0


def test_find_by_id_not_found():
    """find_by_id retorna None quando não existe."""
    repo = PaymentRepositoryMemory()
    assert repo.find_by_id("inexistente") is None


def test_find_by_transaction_id():
    """Buscar por transaction_id."""
    repo = PaymentRepositoryMemory()
    payment = Payment(
        payment_id="pay-1",
        reservation_id="res-1",
        amount=100.0,
        status="PENDING",
        transaction_id="cs_stripe_123",
    )
    repo.save(payment)
    found = repo.find_by_transaction_id("cs_stripe_123")
    assert found is not None
    assert found.transaction_id == "cs_stripe_123"


def test_save_updates_existing():
    """Salvar atualiza pagamento existente."""
    repo = PaymentRepositoryMemory()
    payment = Payment(
        payment_id="pay-1",
        reservation_id="res-1",
        amount=100.0,
        status="PENDING",
    )
    repo.save(payment)
    payment.approve(transaction_id="tx-1")
    repo.save(payment)
    found = repo.find_by_id("pay-1")
    assert found.status == "APPROVED"
    assert found.transaction_id == "tx-1"
