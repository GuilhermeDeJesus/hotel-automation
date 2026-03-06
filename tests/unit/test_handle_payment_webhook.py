"""Testes unitários do HandlePaymentWebhookUseCase."""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.domain.entities.payment.payment import Payment
from app.domain.entities.reservation.reservation import Reservation
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.value_objects.phone_number import PhoneNumber
from app.domain.entities.reservation.stay_period import StayPeriod
from app.application.use_cases.handle_payment_webhook import (
    HandlePaymentWebhookUseCase,
    PaymentWebhookResult,
)


@pytest.fixture
def payment_repo():
    return MagicMock()


@pytest.fixture
def reservation_repo():
    return MagicMock()


@pytest.fixture
def use_case(payment_repo, reservation_repo):
    return HandlePaymentWebhookUseCase(
        payment_repository=payment_repo,
        reservation_repository=reservation_repo,
    )


def test_handle_checkout_completed_approves_payment_and_confirms_reservation(
    use_case, payment_repo, reservation_repo
):
    """checkout.session.completed → Payment.APPROVED → reservation.confirm()."""
    payment = Payment(
        payment_id="pay-1",
        reservation_id="res-1",
        amount=200.0,
        status="PENDING",
    )
    reservation = Reservation(
        reservation_id="res-1",
        guest_name="João",
        guest_phone=PhoneNumber("5561999999999"),
        status=ReservationStatus.PENDING,
        stay_period=StayPeriod(
            date.today(),
            date.today() + timedelta(days=2),
            allow_past=True,
        ),
        room_number="101",
        total_amount=200.0,
    )

    payment_repo.find_by_id.return_value = payment
    reservation_repo.find_by_id.return_value = reservation

    session = {
        "id": "cs_stripe_123",
        "metadata": {"payment_id": "pay-1", "reservation_id": "res-1"},
    }

    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": session},
        }

        result = use_case.handle_stripe_event(
            b"{}",
            "stripe-signature",
            "whsec_test",
        )

    assert result.processed is True
    assert result.reservation_confirmed is True
    assert payment.status == "APPROVED"
    assert payment.transaction_id == "cs_stripe_123"
    assert reservation.status == ReservationStatus.CONFIRMED
    payment_repo.save.assert_called_once()
    reservation_repo.save.assert_called_once()


def test_handle_checkout_completed_payment_not_found(use_case, payment_repo, reservation_repo):
    """Quando Payment não existe, retorna processed=False."""
    payment_repo.find_by_id.return_value = None

    session = {"metadata": {"payment_id": "pay-inexistente"}}

    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": session},
        }

        result = use_case.handle_stripe_event(
            b"{}",
            "stripe-signature",
            "whsec_test",
        )

    assert result.processed is False
    assert "não encontrado" in result.message.lower()


def test_handle_checkout_completed_missing_payment_id(use_case):
    """Quando metadata.payment_id ausente, retorna processed=False."""
    session = {"metadata": {"reservation_id": "res-1"}}

    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": session},
        }

        result = use_case.handle_stripe_event(
            b"{}",
            "stripe-signature",
            "whsec_test",
        )

    assert result.processed is False
    assert "payment_id" in result.message.lower()


def test_handle_checkout_expired_marks_payment_expired(use_case, payment_repo, reservation_repo):
    """checkout.session.expired → Payment.EXPIRED."""
    payment = Payment(
        payment_id="pay-1",
        reservation_id="res-1",
        amount=100.0,
        status="PENDING",
    )
    payment_repo.find_by_id.return_value = payment

    session = {"metadata": {"payment_id": "pay-1"}}

    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = {
            "type": "checkout.session.expired",
            "data": {"object": session},
        }

        result = use_case.handle_stripe_event(
            b"{}",
            "stripe-signature",
            "whsec_test",
        )

    assert result.processed is True
    assert payment.status == "EXPIRED"
    payment_repo.save.assert_called_once()


def test_handle_unknown_event_ignored(use_case):
    """Evento desconhecido é ignorado."""
    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = {
            "type": "customer.created",
            "data": {"object": {}},
        }

        result = use_case.handle_stripe_event(
            b"{}",
            "stripe-signature",
            "whsec_test",
        )

    assert result.processed is True
    assert "ignorado" in result.message.lower()
