"""Payment Repository SQL - implementação com banco de dados."""
from datetime import datetime
from typing import List, Optional
import uuid

from app.domain.entities.payment.payment import Payment
from app.domain.repositories.payment_repository import PaymentRepository
from .models import PaymentModel


class PaymentRepositorySQL(PaymentRepository):
    """Implementação SQL do repositório de pagamentos."""

    def __init__(self, session):
        self.session = session

    @staticmethod
    def _to_domain(model: PaymentModel) -> Payment:
        return Payment(
            payment_id=str(model.id),
            reservation_id=str(model.reservation_id),
            hotel_id=str(model.hotel_id),
            amount=float(model.amount),
            status=model.status,
            payment_method=model.payment_method,
            transaction_id=model.transaction_id,
            created_at=model.created_at,
            approved_at=model.approved_at,
            expires_at=model.expires_at,
        )

    def save(self, hotel_id: str, payment: Payment) -> None:
        existing = (
            self.session.query(PaymentModel)
            .filter_by(id=str(payment.id), hotel_id=hotel_id)
            .first()
            if payment.id else None
        )
        if existing:
            existing.status = payment.status
            existing.transaction_id = payment.transaction_id
            existing.payment_method = payment.payment_method
            existing.approved_at = payment.approved_at
            existing.expires_at = payment.expires_at
            existing.updated_at = datetime.now()
        else:
            new_row = PaymentModel(
                id=str(payment.id) if payment.id else str(uuid.uuid4()),
                reservation_id=str(payment.reservation_id),
                amount=payment.amount,
                status=payment.status,
                payment_method=payment.payment_method,
                transaction_id=payment.transaction_id,
                approved_at=payment.approved_at,
                expires_at=payment.expires_at,
                hotel_id=hotel_id,
            )
            self.session.add(new_row)
            self.session.flush()
            payment.id = str(new_row.id)
        self.session.commit()

    def find_by_id(self, hotel_id: str, payment_id: str) -> Optional[Payment]:
        model = (
            self.session.query(PaymentModel)
            .filter_by(id=str(payment_id), hotel_id=hotel_id)
            .first()
        )
        if not model:
            return None
        return self._to_domain(model)

    def find_by_transaction_id(self, hotel_id: str, transaction_id: str) -> Optional[Payment]:
        model = (
            self.session.query(PaymentModel)
            .filter_by(transaction_id=str(transaction_id), hotel_id=hotel_id)
            .first()
        )
        if not model:
            return None
        return self._to_domain(model)

    def list_payments(
        self,
        hotel_id: str,
        reservation_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Payment]:
        query = self.session.query(PaymentModel).filter_by(hotel_id=hotel_id)
        if reservation_id:
            query = query.filter(PaymentModel.reservation_id == str(reservation_id))
        if status:
            query = query.filter(PaymentModel.status == status.upper())
        models = (
            query.order_by(PaymentModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._to_domain(m) for m in models]

    def find_by_id_global(self, payment_id: str) -> Optional[Payment]:
        """Busca pagamento apenas por ID, sem filtro de hotel (uso especial em webhooks)."""
        model = (
            self.session.query(PaymentModel)
            .filter_by(id=str(payment_id))
            .first()
        )
        if not model:
            return None
        return self._to_domain(model)
