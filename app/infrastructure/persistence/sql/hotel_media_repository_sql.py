from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import and_

from app.domain.entities.hotel.hotel_media import HotelMedia
from app.domain.repositories.hotel_media_repository import HotelMediaRepository

from .models import HotelMediaModel


class HotelMediaRepositorySQL(HotelMediaRepository):
    def __init__(self, session):
        self.session = session

    @staticmethod
    def _normalize_scope(scope: str) -> str:
        s = (scope or "").strip().upper()
        if s in ("HOTEL", "ROOM"):
            return s
        raise ValueError("scope inválido. Use 'HOTEL' ou 'ROOM'.")

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
        scope_n = self._normalize_scope(scope)
        media_id = str(uuid.uuid4())

        model = HotelMediaModel(
            id=media_id,
            hotel_id=hotel_id,
            scope=scope_n,
            room_number=room_number if scope_n == "ROOM" else None,
            caption=caption,
            sort_order=int(sort_order or 0),
            mime_type=mime_type,
            filename=filename,
            data=data,
            is_active=True,
        )
        self.session.add(model)
        self.session.commit()
        return media_id

    def list_media_metadata(
        self,
        hotel_id: str,
        scope: str,
        room_number: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        scope_n = self._normalize_scope(scope)
        query = self.session.query(HotelMediaModel).filter(
            HotelMediaModel.hotel_id == hotel_id,
            HotelMediaModel.scope == scope_n,
            HotelMediaModel.is_active.is_(True),
        )
        if scope_n == "ROOM":
            query = query.filter(HotelMediaModel.room_number == room_number)
        else:
            # Para HOTEL, tratamos room_number sempre como NULL.
            query = query.filter(HotelMediaModel.room_number.is_(None))

        models = (
            query.order_by(HotelMediaModel.sort_order.desc(), HotelMediaModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(m.id),
                "caption": m.caption,
                "mime_type": m.mime_type,
                "filename": m.filename,
                "sort_order": m.sort_order,
                "room_number": m.room_number,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in models
        ]

    def get_media_set_photo_ids(
        self,
        hotel_id: str,
        scope: str,
        room_number: Optional[str] = None,
        limit: int = 3,
    ) -> list[str]:
        scope_n = self._normalize_scope(scope)
        query = self.session.query(HotelMediaModel).filter(
            HotelMediaModel.hotel_id == hotel_id,
            HotelMediaModel.scope == scope_n,
            HotelMediaModel.is_active.is_(True),
        )
        if scope_n == "ROOM":
            query = query.filter(HotelMediaModel.room_number == room_number)
        else:
            query = query.filter(HotelMediaModel.room_number.is_(None))

        models = (
            query.order_by(HotelMediaModel.sort_order.desc(), HotelMediaModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return [str(m.id) for m in models]

    def get_media_by_id(self, media_id: str, hotel_id: str) -> Optional[HotelMedia]:
        model = (
            self.session.query(HotelMediaModel)
            .filter(
                HotelMediaModel.id == str(media_id),
                HotelMediaModel.hotel_id == hotel_id,
                HotelMediaModel.is_active.is_(True),
            )
            .first()
        )
        if not model:
            return None
        return HotelMedia(
            id=str(model.id),
            hotel_id=model.hotel_id,
            scope=model.scope,
            room_number=model.room_number,
            caption=model.caption,
            sort_order=int(model.sort_order or 0),
            mime_type=model.mime_type,
            filename=model.filename,
            data=model.data,
            created_at=model.created_at,
        )

    def get_media_by_id_public(self, media_id: str, hotel_id: str) -> Optional[HotelMedia]:
        model = (
            self.session.query(HotelMediaModel)
            .filter(
                HotelMediaModel.id == str(media_id),
                HotelMediaModel.hotel_id == hotel_id,
                HotelMediaModel.is_active.is_(True),
            )
            .first()
        )
        if not model:
            return None

        return HotelMedia(
            id=str(model.id),
            hotel_id=model.hotel_id,
            scope=model.scope,
            room_number=model.room_number,
            caption=model.caption,
            sort_order=int(model.sort_order or 0),
            mime_type=model.mime_type,
            filename=model.filename,
            data=model.data,
            created_at=model.created_at,
        )

    def deactivate_media(self, media_id: str, hotel_id: str) -> bool:
        model = (
            self.session.query(HotelMediaModel)
            .filter(
                HotelMediaModel.id == str(media_id),
                HotelMediaModel.hotel_id == hotel_id,
                HotelMediaModel.is_active.is_(True),
            )
            .first()
        )
        if not model:
            return False

        model.is_active = False
        self.session.commit()
        return True

