from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.hotel.hotel_media import HotelMedia


class HotelMediaRepository(ABC):
    """Contrato para persistência e busca de mídias (fotos) por hotel/quarto."""

    @abstractmethod
    def save(
        self,
        hotel_id: str,
        scope: str,
        room_number: Optional[str],
        caption: Optional[str],
        mime_type: str,
        filename: Optional[str],
        data: bytes,
        sort_order: int = 0,
    ) -> str:
        """Salva uma mídia e retorna seu ID."""

    @abstractmethod
    def list_media_metadata(
        self,
        hotel_id: str,
        scope: str,
        room_number: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Lista metadados (sem bytes) para o admin panel."""

    @abstractmethod
    def get_media_set_photo_ids(
        self,
        hotel_id: str,
        scope: str,
        room_number: Optional[str] = None,
        limit: int = 3,
    ) -> list[str]:
        """Retorna IDs de uma seleção (ex.: 3 fotos) para envio ao cliente."""

    @abstractmethod
    def get_media_by_id(self, media_id: str, hotel_id: str) -> Optional[HotelMedia]:
        """Busca a mídia por ID respeitando o hotel (multi-tenant)."""

    @abstractmethod
    def get_media_by_id_public(self, media_id: str, hotel_id: str) -> Optional[HotelMedia]:
        """Busca a mídia por ID respeitando o hotel (uso público para provedor via URL tenant-scoped)."""

    @abstractmethod
    def deactivate_media(self, media_id: str, hotel_id: str) -> bool:
        """Desativa (soft-delete) uma mídia específica do hotel."""

