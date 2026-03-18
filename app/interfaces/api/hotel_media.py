"""Admin API para upload e listagem de fotos + rota pública para servir mídia."""

from __future__ import annotations

import io
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.domain.repositories.hotel_media_repository import HotelMediaRepository
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.hotel_media_repository_sql import HotelMediaRepositorySQL
from app.interfaces.dependencies.auth import get_current_user
from app.infrastructure.persistence.sql.models import UserModel


router = APIRouter(prefix="/saas/hotel", tags=["hotel-media"])

_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5MB
_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}


def _infer_mime_type(filename: str | None) -> Optional[str]:
    if not filename:
        return None
    lower = filename.lower()
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    return None


def _normalize_scope(scope: str) -> str:
    s = (scope or "").strip().upper()
    if s not in ("HOTEL", "ROOM"):
        raise HTTPException(status_code=400, detail="scope deve ser HOTEL ou ROOM")
    return s


def _public_media_filename(media_id: str) -> str:
    return f"media-{media_id}.bin"


def get_hotel_media_repo() -> HotelMediaRepository:
    session = SessionLocal()
    try:
        return HotelMediaRepositorySQL(session)
    except Exception:
        session.close()
        raise


@router.post("/media")
async def upload_hotel_media(
    scope: str = Form(...),
    room_number: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
):
    hotel_id = current_user.hotel_id
    if not hotel_id:
        raise HTTPException(status_code=403, detail="Usuário não associado a um hotel.")

    scope_n = _normalize_scope(scope)

    if scope_n == "ROOM" and not room_number:
        raise HTTPException(status_code=400, detail="room_number é obrigatório quando scope=ROOM")

    # Validações de arquivo
    content = await file.read()
    if len(content) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Imagem excede 5MB.")

    mime_type = file.content_type
    if not mime_type or mime_type not in _ALLOWED_MIME:
        inferred = _infer_mime_type(file.filename)
        if inferred and inferred in _ALLOWED_MIME:
            mime_type = inferred
        else:
            raise HTTPException(
                status_code=400,
                detail="Formato inválido. Use apenas jpg/png/webp.",
            )

    repo_session = SessionLocal()
    try:
        repo = HotelMediaRepositorySQL(repo_session)
        media_id = repo.save(
            hotel_id=hotel_id,
            scope=scope_n,
            room_number=room_number,
            caption=caption,
            mime_type=mime_type,
            filename=file.filename,
            data=content,
            sort_order=0,
        )
        return {"success": True, "media_id": media_id}
    finally:
        repo_session.close()


@router.get("/media")
def list_hotel_media(
    scope: str,
    room_number: Optional[str] = None,
    limit: int = 50,
    current_user: UserModel = Depends(get_current_user),
):
    hotel_id = current_user.hotel_id
    if not hotel_id:
        raise HTTPException(status_code=403, detail="Usuário não associado a um hotel.")

    scope_n = _normalize_scope(scope)
    limit_n = int(limit or 50)
    if limit_n < 1:
        limit_n = 50

    session = SessionLocal()
    try:
        repo = HotelMediaRepositorySQL(session)
        items = repo.list_media_metadata(
            hotel_id=hotel_id,
            scope=scope_n,
            room_number=room_number if scope_n == "ROOM" else None,
            limit=limit_n,
        )
        return {"items": items, "success": True}
    finally:
        session.close()


@router.get("/{hotel_id}/media-public/{media_id}")
def get_public_hotel_media_tenant_scoped(hotel_id: str, media_id: str):
    """
    Rota de mídia para provedor (Meta/Twilio), tenant-scoped.
    O `hotel_id` vem na URL para garantir isolamento multi-tenant.
    """
    session = SessionLocal()
    try:
        repo = HotelMediaRepositorySQL(session)
        media = repo.get_media_by_id_public(media_id=media_id, hotel_id=hotel_id)
        if not media:
            raise HTTPException(status_code=404, detail="Mídia não encontrada.")

        stream = io.BytesIO(media.data)
        headers = {
            "Content-Disposition": f'inline; filename="{_public_media_filename(media_id)}"'
        }
        return StreamingResponse(stream, media_type=media.mime_type, headers=headers)
    finally:
        session.close()


@router.get("/media-public/{media_id}")
def get_public_hotel_media_deprecated(media_id: str):
    """
    Endpoint antigo (não tenant-scoped) descontinuado.
    Use: /saas/hotel/{hotel_id}/media-public/{media_id}
    """
    raise HTTPException(
        status_code=404,
        detail="Rota descontinuada. Use /saas/hotel/{hotel_id}/media-public/{media_id}.",
    )


@router.delete("/media/{media_id}")
def delete_hotel_media(
    media_id: str,
    current_user: UserModel = Depends(get_current_user),
):
    hotel_id = current_user.hotel_id
    if not hotel_id:
        raise HTTPException(status_code=403, detail="Usuário não associado a um hotel.")

    session = SessionLocal()
    try:
        repo = HotelMediaRepositorySQL(session)
        ok = repo.deactivate_media(media_id=media_id, hotel_id=hotel_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Mídia não encontrada.")
        return {"success": True}
    finally:
        session.close()

