"""Hotel config API - get and update payment configuration."""
from collections.abc import Generator

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.application.use_cases.get_hotel_config import GetHotelConfigUseCase
from app.application.use_cases.update_hotel_config import UpdateHotelConfigUseCase
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.hotel_repository_sql import HotelRepositorySQL

router = APIRouter(prefix="/saas/hotel", tags=["hotel-config"])


class HotelConfigUpdate(BaseModel):
    """Schema for PATCH /saas/hotel/config."""

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
    use_case: GetHotelConfigUseCase = Depends(get_hotel_config_use_case),
):
    """Get active hotel payment configuration."""
    config = use_case.execute()
    if not config:
        raise HTTPException(status_code=404, detail="Nenhum hotel ativo encontrado.")
    return config


@router.patch("/config")
def update_config(
    body: HotelConfigUpdate,
    use_case: UpdateHotelConfigUseCase = Depends(get_update_hotel_config_use_case),
):
    """Update hotel payment configuration."""
    result = use_case.execute(
        requires_payment_for_confirmation=body.requires_payment_for_confirmation,
        allows_reservation_without_payment=body.allows_reservation_without_payment,
    )
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
