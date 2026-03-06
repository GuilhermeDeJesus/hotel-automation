"""Support Ticket and Room Order Repositories SQL - 6.5, 6.6."""
from app.domain.repositories.support_ticket_repository import SupportTicketRepository
from app.domain.repositories.room_order_repository import RoomOrderRepository
from .models import SupportTicketModel, RoomOrderModel


class SupportTicketRepositorySQL(SupportTicketRepository):
    def __init__(self, session):
        self.session = session

    def save(self, ticket_id: str, reservation_id: str, description: str, category: str) -> None:
        ticket = SupportTicketModel(
            id=ticket_id,
            reservation_id=reservation_id,
            description=description,
            category=category,
            status="OPEN",
        )
        self.session.add(ticket)
        self.session.commit()


class RoomOrderRepositorySQL(RoomOrderRepository):
    """6.5 Room orders."""
    def __init__(self, session):
        self.session = session

    def save(self, order_id: str, reservation_id: str, items_json: str, total: float) -> None:
        order = RoomOrderModel(
            id=order_id,
            reservation_id=reservation_id,
            items_json=items_json,
            total_amount=total,
            status="PENDING",
        )
        self.session.add(order)
        self.session.commit()
