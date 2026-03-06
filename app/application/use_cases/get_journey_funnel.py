"""Get journey funnel: Lead → Reserva → Confirmada → Check-in → Check-out."""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

from app.domain.repositories.reservation_repository import ReservationRepository


class GetJourneyFunnelUseCase:
    """Aggregates leads + reservations into the full journey funnel."""

    def __init__(
        self,
        saas_repository: Any,
        reservation_repository: ReservationRepository,
    ):
        self.saas_repository = saas_repository
        self.reservation_repository = reservation_repository

    def execute(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict[str, Any]:
        """
        Return journey funnel stages: Lead, Reserva, Confirmada, Check-in, Check-out.
        Leads come from saas_repository; reservation counts from reservation_repository.
        """
        lead_funnel = self.saas_repository.get_funnel(from_date, to_date)
        leads_total = lead_funnel.get("total", 0)

        res_counts = self.reservation_repository.count_by_status(from_date, to_date)
        pending = res_counts.get("PENDING", 0)
        confirmed = res_counts.get("CONFIRMED", 0)
        checked_in = res_counts.get("CHECKED_IN", 0)
        checked_out = res_counts.get("CHECKED_OUT", 0)

        stages = [
            {"stage": "LEAD", "count": leads_total, "label": "Lead"},
            {"stage": "RESERVA", "count": pending, "label": "Reserva"},
            {"stage": "CONFIRMADA", "count": confirmed + checked_in + checked_out, "label": "Confirmada"},
            {"stage": "CHECK_IN", "count": checked_in + checked_out, "label": "Check-in"},
            {"stage": "CHECK_OUT", "count": checked_out, "label": "Check-out"},
        ]

        return {
            "stages": stages,
            "total": leads_total,
        }
