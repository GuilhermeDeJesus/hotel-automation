"""Rooms API - CRUD for hotel rooms."""
from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.application.use_cases.list_rooms import ListRoomsUseCase
from app.application.use_cases.create_room import CreateRoomUseCase
from app.application.use_cases.update_room import UpdateRoomUseCase
from app.application.use_cases.delete_room import DeleteRoomUseCase
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.room_repository_sql import RoomRepositorySQL

router = APIRouter(prefix="/saas/rooms", tags=["rooms"])


class CreateRoomRequest(BaseModel):
    number: str
    room_type: str
    daily_rate: float
    max_guests: int


class UpdateRoomRequest(BaseModel):
    room_type: str | None = None
    daily_rate: float | None = None
    max_guests: int | None = None
    status: str | None = None


def get_list_rooms_use_case() -> Generator[ListRoomsUseCase, None, None]:
    session = SessionLocal()
    try:
        repo = RoomRepositorySQL(session)
        yield ListRoomsUseCase(repo)
    finally:
        session.close()


def get_create_room_use_case() -> Generator[CreateRoomUseCase, None, None]:
    session = SessionLocal()
    try:
        repo = RoomRepositorySQL(session)
        yield CreateRoomUseCase(repo)
    finally:
        session.close()


def get_update_room_use_case() -> Generator[UpdateRoomUseCase, None, None]:
    session = SessionLocal()
    try:
        repo = RoomRepositorySQL(session)
        yield UpdateRoomUseCase(repo)
    finally:
        session.close()


def get_delete_room_use_case() -> Generator[DeleteRoomUseCase, None, None]:
    session = SessionLocal()
    try:
        repo = RoomRepositorySQL(session)
        yield DeleteRoomUseCase(repo)
    finally:
        session.close()


@router.get("")
def list_rooms(
    use_case: ListRoomsUseCase = Depends(get_list_rooms_use_case),
):
    """List all active rooms."""
    return {"items": use_case.execute()}


@router.post("")
def create_room(
    body: CreateRoomRequest,
    use_case: CreateRoomUseCase = Depends(get_create_room_use_case),
):
    """Create a new room."""
    result = use_case.execute(
        number=body.number,
        room_type=body.room_type,
        daily_rate=body.daily_rate,
        max_guests=body.max_guests,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result["room"]


@router.patch("/{room_number}")
def update_room(
    room_number: str,
    body: UpdateRoomRequest,
    use_case: UpdateRoomUseCase = Depends(get_update_room_use_case),
):
    """Update a room by number."""
    result = use_case.execute(
        room_number=room_number,
        room_type=body.room_type,
        daily_rate=body.daily_rate,
        max_guests=body.max_guests,
        status=body.status,
    )
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result["room"]


@router.delete("/{room_number}")
def delete_room(
    room_number: str,
    use_case: DeleteRoomUseCase = Depends(get_delete_room_use_case),
):
    """Soft delete (deactivate) a room."""
    result = use_case.execute(room_number=room_number)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"message": result["message"]}
