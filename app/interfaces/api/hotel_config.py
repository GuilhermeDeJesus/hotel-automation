"""Hotel config API - get and update hotel configuration."""
from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.application.use_cases.get_hotel_config import GetHotelConfigUseCase
from app.application.use_cases.update_hotel_config import UpdateHotelConfigUseCase
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.hotel_repository_sql import HotelRepositorySQL
from app.interfaces.dependencies.auth import get_current_user
from app.infrastructure.persistence.sql.models import UserModel

router = APIRouter(prefix="/saas/hotel", tags=["hotel-config"])


class HotelConfigUpdate(BaseModel):
    """Schema for PATCH /saas/hotel/config."""

    name: str | None = None
    address: str | None = None
    contact_phone: str | None = None
    checkin_time: str | None = None
    checkout_time: str | None = None
    cancellation_policy: str | None = None
    pet_policy: str | None = None
    child_policy: str | None = None
    amenities: str | None = None
    requires_payment_for_confirmation: bool | None = None
    allows_reservation_without_payment: bool | None = None


def get_hotel_config_use_case() -> Generator[GetHotelConfigUseCase, None, None]:
    session = SessionLocal()
    try:
        repo = HotelRepositorySQL(session)
        yield GetHotelConfigUseCase(hotel_repository=repo)
    finally:
        session.close()


def get_update_hotel_config_use_case() -> Generator[UpdateHotelConfigUseCase, None, None]:
    session = SessionLocal()
    try:
        repo = HotelRepositorySQL(session)
        yield UpdateHotelConfigUseCase(hotel_repository=repo)
    finally:
        session.close()


@router.get("/config")
def get_config(
    current_user: UserModel = Depends(get_current_user),
    use_case: GetHotelConfigUseCase = Depends(get_hotel_config_use_case),
):
    """Get active hotel payment configuration for the current user's hotel."""
    hotel_id = current_user.hotel_id
    if not hotel_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não associado a um hotel",
        )

    config = use_case.execute(hotel_id=hotel_id)
    if not config:
        raise HTTPException(status_code=404, detail="Nenhum hotel ativo encontrado.")
    return config


@router.patch("/config")
def update_config(
    body: HotelConfigUpdate,
    current_user: UserModel = Depends(get_current_user),
    use_case: UpdateHotelConfigUseCase = Depends(get_update_hotel_config_use_case),
):
    """Update configuration for the current user's hotel."""
    hotel_id = current_user.hotel_id
    if not hotel_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não associado a um hotel",
        )

    result = use_case.execute(
        hotel_id=hotel_id,
        name=body.name,
        address=body.address,
        contact_phone=body.contact_phone,
        checkin_time=body.checkin_time,
        checkout_time=body.checkout_time,
        cancellation_policy=body.cancellation_policy,
        pet_policy=body.pet_policy,
        child_policy=body.child_policy,
        amenities=body.amenities,
        requires_payment_for_confirmation=body.requires_payment_for_confirmation,
        allows_reservation_without_payment=body.allows_reservation_without_payment,
    )
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
