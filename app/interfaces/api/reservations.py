"""Reservations API - list and manage reservations."""
from collections.abc import Generator
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.use_cases.list_reservations import ListReservationsUseCase
from app.application.use_cases.mark_no_show_reservation import MarkNoShowReservationUseCase
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.reservation_repository_sql import ReservationRepositorySQL

router = APIRouter(prefix="/saas/reservations", tags=["reservations"])


def get_list_reservations_use_case() -> Generator[ListReservationsUseCase, None, None]:
    session = SessionLocal()
    try:
        repo = ReservationRepositorySQL(session)
        yield ListReservationsUseCase(reservation_repository=repo)
    finally:
        session.close()


def get_mark_no_show_use_case() -> Generator[MarkNoShowReservationUseCase, None, None]:
    session = SessionLocal()
    try:
        repo = ReservationRepositorySQL(session)
        yield MarkNoShowReservationUseCase(reservation_repository=repo)
    finally:
        session.close()


@router.get("")
def list_reservations(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    status: str | None = Query(default=None),
    room_number: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    use_case: ListReservationsUseCase = Depends(get_list_reservations_use_case),
):
    """List reservations with optional filters."""
    items = use_case.execute(
        from_date=from_date,
        to_date=to_date,
        status=status,
        room_number=room_number,
        limit=limit,
    )
    return {"items": items}


@router.post("/{reservation_id}/mark-no-show")
def mark_no_show(
    reservation_id: str,
    use_case: MarkNoShowReservationUseCase = Depends(get_mark_no_show_use_case),
):
    """Mark a CONFIRMED reservation as no-show."""
    result = use_case.execute(reservation_id)
    if result["success"]:
        return result
    raise HTTPException(status_code=400, detail=result["error"])
