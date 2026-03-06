"""
Room Order Use Case - 6.5 Pedidos durante a estadia.

Cardápio de room service, toalhas extras, etc.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import json
import uuid

from app.domain.repositories.reservation_repository import ReservationRepository
from app.domain.repositories.room_order_repository import RoomOrderRepository


@dataclass
class OrderItemDTO:
    name: str
    quantity: int
    unit_price: float


@dataclass
class RoomOrderRequestDTO:
    phone: str
    items: List[OrderItemDTO]


@dataclass
class RoomOrderResponseDTO:
    success: bool
    message: str
    order_id: Optional[str] = None


class RoomOrderUseCase:
    """6.5 Pedidos durante a estadia (room service)."""

    MENU = [
        {"id": "cafe", "name": "Café da manhã", "price": 35.0},
        {"id": "almoco", "name": "Almoço", "price": 45.0},
        {"id": "jantar", "name": "Jantar", "price": 50.0},
        {"id": "toalha", "name": "Toalha extra", "price": 15.0},
        {"id": "agua", "name": "Água mineral", "price": 10.0},
    ]

    def __init__(
        self,
        reservation_repository: ReservationRepository,
        order_repository: RoomOrderRepository,
    ):
        self.reservation_repository = reservation_repository
        self.order_repository = order_repository

    def execute(self, request: RoomOrderRequestDTO) -> RoomOrderResponseDTO:
        reservation = self.reservation_repository.find_by_phone_number(request.phone)
        if not reservation:
            return RoomOrderResponseDTO(success=False, message="Nenhuma reserva encontrada.")

        if reservation.status.name != "CHECKED_IN":
            return RoomOrderResponseDTO(
                success=False,
                message="Pedidos disponíveis apenas durante a hospedagem.",
            )

        if not request.items:
            return RoomOrderResponseDTO(success=False, message="Informe os itens desejados.")

        total = sum(item.quantity * item.unit_price for item in request.items)
        items_data = [
            {"name": i.name, "quantity": i.quantity, "unit_price": i.unit_price}
            for i in request.items
        ]
        order_id = str(uuid.uuid4())[:8]
        self.order_repository.save(
            order_id=order_id,
            reservation_id=reservation.id,
            items_json=json.dumps(items_data),
            total=total,
        )

        return RoomOrderResponseDTO(
            success=True,
            message=f"✅ Pedido #{order_id} registrado! Total: R$ {total:.2f}",
            order_id=order_id,
        )

    @classmethod
    def get_menu_text(cls) -> str:
        """Retorna cardápio formatado para exibição."""
        lines = ["📋 Room Service:\n"]
        for item in cls.MENU:
            lines.append(f"- {item['name']}: R$ {item['price']:.2f}")
        lines.append("\nResponda com o item e quantidade (ex: Café 2, Água 3)")
        return "\n".join(lines)
