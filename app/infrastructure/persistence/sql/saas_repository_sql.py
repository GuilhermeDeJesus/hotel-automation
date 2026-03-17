from __future__ import annotations

import json
import uuid
from datetime import datetime, date, time, timedelta
from typing import Any

from sqlalchemy import func, select

from .models import AnalyticsEventModel, LeadModel, ReservationModel, SaaSAdminAuditEventModel, SaaSAuditMetricsSnapshotModel


class SaaSRepositorySQL:
    def __init__(self, session):
        self.session = session

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        return "".join(ch for ch in str(phone or "") if ch.isdigit())

    @staticmethod
    def _start_of_day(value: date | None) -> datetime | None:
        if value is None:
            return None
        return datetime.combine(value, time.min)

    @staticmethod
    def _end_of_day(value: date | None) -> datetime | None:
        if value is None:
            return None
        return datetime.combine(value, time.max)

    @staticmethod
    def _normalize_source(source: str | None) -> str | None:
        if not source:
            return None
        return source.lower().strip()

    @staticmethod
    def _normalize_stage(stage: str | None) -> str | None:
        if not stage:
            return None
        return stage.upper().strip()

    @staticmethod
    def _normalize_granularity(granularity: str | None) -> str:
        normalized = (granularity or "day").lower().strip()
        return normalized if normalized in {"day", "week", "month"} else "day"

    def _resolve_period(self, start_date: date | None, end_date: date | None) -> tuple[datetime, datetime]:
        if start_date is None and end_date is None:
            today = datetime.now().date()
            start_dt = self._start_of_day(today - timedelta(days=6))
            end_dt = self._end_of_day(today)
            return start_dt, end_dt

        if start_date is None and end_date is not None:
            start_dt = self._start_of_day(end_date - timedelta(days=6))
            end_dt = self._end_of_day(end_date)
            return start_dt, end_dt

        if start_date is not None and end_date is None:
            start_dt = self._start_of_day(start_date)
            end_dt = self._end_of_day(start_date + timedelta(days=6))
            return start_dt, end_dt

        return self._start_of_day(start_date), self._end_of_day(end_date)

    def _build_filtered_phones_select(self, source: str | None, stage: str | None):
        lead_phone_query = select(LeadModel.phone_number)
        if source:
            lead_phone_query = lead_phone_query.where(LeadModel.source == source)
        if stage:
            lead_phone_query = lead_phone_query.where(LeadModel.stage == stage)
        return lead_phone_query

    @staticmethod
    def _base_kpi_payload(payload: dict[str, Any]) -> dict[str, Any]:
        keys = [
            "leads_captured",
            "ai_response_rate",
            "reservation_confirmation_rate",
            "checkins_completed",
            "avg_response_time_seconds",
            "conversion_by_source",
        ]
        return {key: payload.get(key) for key in keys}

    def get_timeseries(
        self,
        start_date: date | None,
        end_date: date | None,
        source: str | None = None,
        status: str | None = None,
        granularity: str | None = None,
    ) -> dict[str, Any]:
        start_dt, end_dt = self._resolve_period(start_date, end_date)
        normalized_source = self._normalize_source(source)
        normalized_stage = self._normalize_stage(status)
        normalized_granularity = self._normalize_granularity(granularity)
        filtered_phones_select = self._build_filtered_phones_select(normalized_source, normalized_stage)

        day_points = self._build_daily_series(
            start_dt=start_dt,
            end_dt=end_dt,
            source=normalized_source,
            stage=normalized_stage,
            filtered_phones_select=filtered_phones_select,
        )
        points = self._aggregate_series(day_points, normalized_granularity)

        return {
            "granularity": normalized_granularity,
            "period": {
                "from": start_dt.date().isoformat(),
                "to": end_dt.date().isoformat(),
                "source": normalized_source,
                "status": normalized_stage,
            },
            "points": points,
        }

    def get_kpis_comparison(
        self,
        start_date: date | None,
        end_date: date | None,
        source: str | None = None,
        status: str | None = None,
        granularity: str | None = None,
    ) -> dict[str, Any]:
        current_start_dt, current_end_dt = self._resolve_period(start_date, end_date)
        normalized_granularity = self._normalize_granularity(granularity)
        window_days = (current_end_dt.date() - current_start_dt.date()).days + 1

        previous_end_date = current_start_dt.date() - timedelta(days=1)
        previous_start_date = previous_end_date - timedelta(days=window_days - 1)

        current_payload = self.get_kpis(
            start_date=current_start_dt.date(),
            end_date=current_end_dt.date(),
            source=source,
            status=status,
        )
        previous_payload = self.get_kpis(
            start_date=previous_start_date,
            end_date=previous_end_date,
            source=source,
            status=status,
        )

        current_base = self._base_kpi_payload(current_payload)
        previous_base = self._base_kpi_payload(previous_payload)

        current_series = self.get_timeseries(
            start_date=current_start_dt.date(),
            end_date=current_end_dt.date(),
            source=source,
            status=status,
            granularity=normalized_granularity,
        )
        previous_series = self.get_timeseries(
            start_date=previous_start_date,
            end_date=previous_end_date,
            source=source,
            status=status,
            granularity=normalized_granularity,
        )

        deltas: dict[str, Any] = {}
        for key in [
            "leads_captured",
            "ai_response_rate",
            "reservation_confirmation_rate",
            "checkins_completed",
            "avg_response_time_seconds",
        ]:
            current_value = float(current_base.get(key) or 0)
            previous_value = float(previous_base.get(key) or 0)
            absolute = current_value - previous_value
            percent = None if previous_value == 0 else round((absolute / previous_value) * 100, 3)
            deltas[key] = {
                "absolute": round(absolute, 3),
                "percent": percent,
            }

        return {
            "granularity": normalized_granularity,
            "current_period": current_payload.get("period"),
            "previous_period": previous_payload.get("period"),
            "current": current_base,
            "previous": previous_base,
            "delta": deltas,
            "series_current": current_series.get("points", []),
            "series_previous": previous_series.get("points", []),
        }

    def _aggregate_series(self, day_points: list[dict[str, Any]], granularity: str) -> list[dict[str, Any]]:
        if granularity == "day":
            return day_points

        grouped: dict[str, dict[str, Any]] = {}
        for point in day_points:
            day_date = datetime.strptime(point["date"], "%Y-%m-%d").date()

            if granularity == "week":
                bucket_date = day_date - timedelta(days=day_date.weekday())
            else:  # month
                bucket_date = day_date.replace(day=1)

            bucket_key = bucket_date.isoformat()
            agg = grouped.setdefault(
                bucket_key,
                {
                    "date": bucket_key,
                    "leads": 0,
                    "inbound_messages": 0,
                    "outbound_messages": 0,
                    "confirmed_reservations": 0,
                    "checkins": 0,
                    "_response_weighted_sum": 0.0,
                },
            )

            agg["leads"] += int(point.get("leads", 0))
            agg["inbound_messages"] += int(point.get("inbound_messages", 0))
            agg["outbound_messages"] += int(point.get("outbound_messages", 0))
            agg["confirmed_reservations"] += int(point.get("confirmed_reservations", 0))
            agg["checkins"] += int(point.get("checkins", 0))

            outbound_count = int(point.get("outbound_messages", 0))
            response_seconds = float(point.get("avg_response_time_seconds", 0.0))
            agg["_response_weighted_sum"] += response_seconds * outbound_count

        result: list[dict[str, Any]] = []
        for bucket_key in sorted(grouped.keys()):
            bucket = grouped[bucket_key]
            outbound = bucket["outbound_messages"]
            avg_response = (bucket["_response_weighted_sum"] / outbound) if outbound else 0.0
            result.append(
                {
                    "date": bucket["date"],
                    "leads": bucket["leads"],
                    "inbound_messages": bucket["inbound_messages"],
                    "outbound_messages": bucket["outbound_messages"],
                    "confirmed_reservations": bucket["confirmed_reservations"],
                    "checkins": bucket["checkins"],
                    "avg_response_time_seconds": round(avg_response, 3),
                }
            )

        return result

    def track_event(
        self,
        phone: str,
        source: str,
        event_type: str,
        success: bool = True,
        response_time_ms: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        normalized_phone = self._normalize_phone(phone)
        if not normalized_phone:
            return

        row = AnalyticsEventModel(
            phone_number=normalized_phone,
            source=(source or "unknown").lower(),
            event_type=event_type,
            success=success,
            response_time_ms=response_time_ms,
            details=json.dumps(details or {}, ensure_ascii=False),
        )
        self.session.add(row)
        self.session.commit()

    def touch_lead(self, hotel_id: str, phone: str, source: str, stage: str = "NEW") -> LeadModel | None:
        normalized_phone = self._normalize_phone(phone)
        if not normalized_phone:
            return None

        now = datetime.now()
        lead: LeadModel | None = (
            self.session.query(LeadModel)
            .filter_by(phone_number=normalized_phone, hotel_id=hotel_id)
            .first()
        )

        if lead is None:
            lead = LeadModel(
                id=str(uuid.uuid4()),
                hotel_id=hotel_id,
                phone_number=normalized_phone,
                source=(source or "unknown").lower(),
                stage=stage,
                message_count=1,
                first_seen_at=now,
                last_seen_at=now,
            )
            self.session.add(lead)
        else:
            lead.source = (source or lead.source or "unknown").lower()
            lead.last_seen_at = now
            lead.message_count = (lead.message_count or 0) + 1
            if self._stage_rank(stage) > self._stage_rank(lead.stage):
                lead.stage = stage

        self.session.commit()
        return lead

    def sync_lead_stage_from_reservation(self, phone: str) -> None:
        normalized_phone = self._normalize_phone(phone)
        if not normalized_phone:
            return

        lead: LeadModel | None = (
            self.session.query(LeadModel)
            .filter_by(phone_number=normalized_phone)
            .first()
        )
        if lead is None:
            return

        reservation: ReservationModel | None = (
            self.session.query(ReservationModel)
            .filter_by(guest_phone=normalized_phone)
            .order_by(ReservationModel.updated_at.desc())
            .first()
        )
        if reservation is None:
            return

        status = (reservation.status or "").upper()
        mapped_stage = {
            "PENDING": "RESERVATION_PENDING",
            "CONFIRMED": "RESERVATION_CONFIRMED",
            "CHECKED_IN": "CHECKED_IN",
        }.get(status)
        if mapped_stage and self._stage_rank(mapped_stage) > self._stage_rank(lead.stage):
            lead.stage = mapped_stage
            self.session.commit()

    def get_kpis(
        self,
        start_date: date | None,
        end_date: date | None,
        source: str | None = None,
        status: str | None = None,
        granularity: str | None = None,
    ) -> dict[str, Any]:
        start_dt, end_dt = self._resolve_period(start_date, end_date)
        normalized_source = self._normalize_source(source)
        normalized_stage = self._normalize_stage(status)
        normalized_granularity = self._normalize_granularity(granularity)
        filtered_phones_select = self._build_filtered_phones_select(normalized_source, normalized_stage)

        lead_query = self.session.query(func.count(LeadModel.id))
        lead_query = lead_query.filter(LeadModel.first_seen_at >= start_dt)
        lead_query = lead_query.filter(LeadModel.first_seen_at <= end_dt)
        if normalized_source:
            lead_query = lead_query.filter(LeadModel.source == normalized_source)
        if normalized_stage:
            lead_query = lead_query.filter(LeadModel.stage == normalized_stage)
        leads_captured = int(lead_query.scalar() or 0)

        inbound_q = self.session.query(func.count(AnalyticsEventModel.id)).filter(
            AnalyticsEventModel.event_type == "inbound_message"
        )
        outbound_q = self.session.query(func.count(AnalyticsEventModel.id)).filter(
            AnalyticsEventModel.event_type == "outbound_message",
            AnalyticsEventModel.success.is_(True),
        )
        inbound_q = inbound_q.filter(AnalyticsEventModel.created_at >= start_dt)
        outbound_q = outbound_q.filter(AnalyticsEventModel.created_at >= start_dt)
        inbound_q = inbound_q.filter(AnalyticsEventModel.created_at <= end_dt)
        outbound_q = outbound_q.filter(AnalyticsEventModel.created_at <= end_dt)
        if normalized_source:
            inbound_q = inbound_q.filter(AnalyticsEventModel.source == normalized_source)
            outbound_q = outbound_q.filter(AnalyticsEventModel.source == normalized_source)
        if normalized_source or normalized_stage:
            inbound_q = inbound_q.filter(AnalyticsEventModel.phone_number.in_(filtered_phones_select))
            outbound_q = outbound_q.filter(AnalyticsEventModel.phone_number.in_(filtered_phones_select))

        inbound_count = int(inbound_q.scalar() or 0)
        outbound_count = int(outbound_q.scalar() or 0)
        ai_response_rate = (outbound_count / inbound_count) if inbound_count else 0.0

        reservation_q = self.session.query(ReservationModel)
        reservation_q = reservation_q.filter(ReservationModel.created_at >= start_dt)
        reservation_q = reservation_q.filter(ReservationModel.created_at <= end_dt)
        if normalized_source or normalized_stage:
            reservation_q = reservation_q.filter(ReservationModel.guest_phone.in_(filtered_phones_select))

        total_reservations = reservation_q.count()
        confirmed_reservations = reservation_q.filter(ReservationModel.status == "CONFIRMED").count()
        reservation_confirmation_rate = (
            confirmed_reservations / total_reservations if total_reservations else 0.0
        )

        checkins_q = self.session.query(func.count(ReservationModel.id)).filter(
            ReservationModel.status == "CHECKED_IN"
        )
        checkins_q = checkins_q.filter(ReservationModel.updated_at >= start_dt)
        checkins_q = checkins_q.filter(ReservationModel.updated_at <= end_dt)
        if normalized_source or normalized_stage:
            checkins_q = checkins_q.filter(ReservationModel.guest_phone.in_(filtered_phones_select))
        checkins_completed = int(checkins_q.scalar() or 0)

        avg_resp_q = self.session.query(func.avg(AnalyticsEventModel.response_time_ms)).filter(
            AnalyticsEventModel.event_type == "outbound_message",
            AnalyticsEventModel.response_time_ms.isnot(None),
        )
        avg_resp_q = avg_resp_q.filter(AnalyticsEventModel.created_at >= start_dt)
        avg_resp_q = avg_resp_q.filter(AnalyticsEventModel.created_at <= end_dt)
        if normalized_source:
            avg_resp_q = avg_resp_q.filter(AnalyticsEventModel.source == normalized_source)
        if normalized_source or normalized_stage:
            avg_resp_q = avg_resp_q.filter(AnalyticsEventModel.phone_number.in_(filtered_phones_select))
        avg_ms = avg_resp_q.scalar()
        avg_response_time_seconds = (float(avg_ms) / 1000.0) if avg_ms else 0.0

        by_source_q = self.session.query(
            LeadModel.source,
            func.count(LeadModel.id),
        )
        by_source_q = by_source_q.filter(LeadModel.first_seen_at >= start_dt)
        by_source_q = by_source_q.filter(LeadModel.first_seen_at <= end_dt)
        if normalized_source:
            by_source_q = by_source_q.filter(LeadModel.source == normalized_source)
        if normalized_stage:
            by_source_q = by_source_q.filter(LeadModel.stage == normalized_stage)
        by_source_rows = by_source_q.group_by(LeadModel.source).all()
        conversion_by_source = {source: int(count) for source, count in by_source_rows}

        daily_series = self._build_daily_series(
            start_dt=start_dt,
            end_dt=end_dt,
            source=normalized_source,
            stage=normalized_stage,
            filtered_phones_select=filtered_phones_select,
        )
        series = self._aggregate_series(daily_series, normalized_granularity)

        return {
            "leads_captured": leads_captured,
            "ai_response_rate": round(ai_response_rate, 4),
            "reservation_confirmation_rate": round(reservation_confirmation_rate, 4),
            "checkins_completed": checkins_completed,
            "avg_response_time_seconds": round(avg_response_time_seconds, 3),
            "conversion_by_source": conversion_by_source,
            "period": {
                "from": start_dt.date().isoformat(),
                "to": end_dt.date().isoformat(),
                "source": normalized_source,
                "status": normalized_stage,
                "granularity": normalized_granularity,
            },
            "granularity": normalized_granularity,
            "series": series,
            "daily_series": daily_series,
        }

    def _build_daily_series(
        self,
        start_dt: datetime,
        end_dt: datetime,
        source: str | None,
        stage: str | None,
        filtered_phones_select,
    ) -> list[dict[str, Any]]:
        leads_by_day_q = self.session.query(
            func.date(LeadModel.first_seen_at).label("day"),
            func.count(LeadModel.id),
        )
        leads_by_day_q = leads_by_day_q.filter(LeadModel.first_seen_at >= start_dt)
        leads_by_day_q = leads_by_day_q.filter(LeadModel.first_seen_at <= end_dt)
        if source:
            leads_by_day_q = leads_by_day_q.filter(LeadModel.source == source)
        if stage:
            leads_by_day_q = leads_by_day_q.filter(LeadModel.stage == stage)
        leads_by_day = {str(day): int(count) for day, count in leads_by_day_q.group_by("day").all()}

        inbound_by_day_q = self.session.query(
            func.date(AnalyticsEventModel.created_at).label("day"),
            func.count(AnalyticsEventModel.id),
        ).filter(
            AnalyticsEventModel.event_type == "inbound_message",
            AnalyticsEventModel.created_at >= start_dt,
            AnalyticsEventModel.created_at <= end_dt,
        )
        outbound_by_day_q = self.session.query(
            func.date(AnalyticsEventModel.created_at).label("day"),
            func.count(AnalyticsEventModel.id),
        ).filter(
            AnalyticsEventModel.event_type == "outbound_message",
            AnalyticsEventModel.success.is_(True),
            AnalyticsEventModel.created_at >= start_dt,
            AnalyticsEventModel.created_at <= end_dt,
        )
        avg_resp_by_day_q = self.session.query(
            func.date(AnalyticsEventModel.created_at).label("day"),
            func.avg(AnalyticsEventModel.response_time_ms),
        ).filter(
            AnalyticsEventModel.event_type == "outbound_message",
            AnalyticsEventModel.response_time_ms.isnot(None),
            AnalyticsEventModel.created_at >= start_dt,
            AnalyticsEventModel.created_at <= end_dt,
        )

        if source:
            inbound_by_day_q = inbound_by_day_q.filter(AnalyticsEventModel.source == source)
            outbound_by_day_q = outbound_by_day_q.filter(AnalyticsEventModel.source == source)
            avg_resp_by_day_q = avg_resp_by_day_q.filter(AnalyticsEventModel.source == source)

        if source or stage:
            inbound_by_day_q = inbound_by_day_q.filter(AnalyticsEventModel.phone_number.in_(filtered_phones_select))
            outbound_by_day_q = outbound_by_day_q.filter(AnalyticsEventModel.phone_number.in_(filtered_phones_select))
            avg_resp_by_day_q = avg_resp_by_day_q.filter(AnalyticsEventModel.phone_number.in_(filtered_phones_select))

        inbound_by_day = {str(day): int(count) for day, count in inbound_by_day_q.group_by("day").all()}
        outbound_by_day = {str(day): int(count) for day, count in outbound_by_day_q.group_by("day").all()}
        avg_resp_by_day = {
            str(day): round((float(avg_ms) / 1000.0), 3)
            for day, avg_ms in avg_resp_by_day_q.group_by("day").all()
            if avg_ms is not None
        }

        confirmed_by_day_q = self.session.query(
            func.date(ReservationModel.updated_at).label("day"),
            func.count(ReservationModel.id),
        ).filter(
            ReservationModel.status == "CONFIRMED",
            ReservationModel.updated_at >= start_dt,
            ReservationModel.updated_at <= end_dt,
        )
        checkins_by_day_q = self.session.query(
            func.date(ReservationModel.updated_at).label("day"),
            func.count(ReservationModel.id),
        ).filter(
            ReservationModel.status == "CHECKED_IN",
            ReservationModel.updated_at >= start_dt,
            ReservationModel.updated_at <= end_dt,
        )
        if source or stage:
            confirmed_by_day_q = confirmed_by_day_q.filter(ReservationModel.guest_phone.in_(filtered_phones_select))
            checkins_by_day_q = checkins_by_day_q.filter(ReservationModel.guest_phone.in_(filtered_phones_select))

        confirmed_by_day = {str(day): int(count) for day, count in confirmed_by_day_q.group_by("day").all()}
        checkins_by_day = {str(day): int(count) for day, count in checkins_by_day_q.group_by("day").all()}

        points: list[dict[str, Any]] = []
        current_day = start_dt.date()
        final_day = end_dt.date()
        while current_day <= final_day:
            day_key = current_day.isoformat()
            points.append(
                {
                    "date": day_key,
                    "leads": leads_by_day.get(day_key, 0),
                    "inbound_messages": inbound_by_day.get(day_key, 0),
                    "outbound_messages": outbound_by_day.get(day_key, 0),
                    "confirmed_reservations": confirmed_by_day.get(day_key, 0),
                    "checkins": checkins_by_day.get(day_key, 0),
                    "avg_response_time_seconds": avg_resp_by_day.get(day_key, 0.0),
                }
            )
            current_day += timedelta(days=1)

        return points

    def list_leads(
        self,
        hotel_id: str,
        start_date: date | None,
        end_date: date | None,
        status: str | None,
    ) -> list[dict[str, Any]]:
        start_dt = self._start_of_day(start_date)
        end_dt = self._end_of_day(end_date)

        query = self.session.query(LeadModel).filter(LeadModel.hotel_id == hotel_id)
        if start_dt:
            query = query.filter(LeadModel.first_seen_at >= start_dt)
        if end_dt:
            query = query.filter(LeadModel.first_seen_at <= end_dt)
        if status:
            query = query.filter(LeadModel.stage == status.upper())

        rows = query.order_by(LeadModel.last_seen_at.desc()).limit(500).all()
        return [
            {
                "id": row.id,
                "phone_number": row.phone_number,
                "source": row.source,
                "stage": row.stage,
                "message_count": row.message_count,
                "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
                "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
            }
            for row in rows
        ]

    def get_funnel(
        self,
        hotel_id: str,
        start_date: date | None,
        end_date: date | None,
    ) -> dict[str, Any]:
        start_dt = self._start_of_day(start_date)
        end_dt = self._end_of_day(end_date)

        query = self.session.query(LeadModel.stage, func.count(LeadModel.id)).filter(
            LeadModel.hotel_id == hotel_id
        )
        if start_dt:
            query = query.filter(LeadModel.first_seen_at >= start_dt)
        if end_dt:
            query = query.filter(LeadModel.first_seen_at <= end_dt)

        rows = query.group_by(LeadModel.stage).all()
        counts = {stage: int(count) for stage, count in rows}

        ordered = [
            "NEW",
            "ENGAGED",
            "RESERVATION_PENDING",
            "RESERVATION_CONFIRMED",
            "CHECKED_IN",
        ]

        return {
            "stages": [{"stage": stage, "count": counts.get(stage, 0)} for stage in ordered],
            "total": sum(counts.values()),
        }

    def list_admin_audit_events(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        outcome: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        normalized_outcome = (outcome or "").strip().lower() or None
        safe_page = max(1, int(page or 1))
        safe_page_size = min(100, max(1, int(page_size or 20)))
        offset = (safe_page - 1) * safe_page_size

        query = self.session.query(SaaSAdminAuditEventModel)

        start_dt = self._start_of_day(start_date)
        end_dt = self._end_of_day(end_date)
        if start_dt:
            query = query.filter(SaaSAdminAuditEventModel.created_at >= start_dt)
        if end_dt:
            query = query.filter(SaaSAdminAuditEventModel.created_at <= end_dt)
        if normalized_outcome:
            query = query.filter(SaaSAdminAuditEventModel.outcome == normalized_outcome)

        total = int(query.count())
        rows = (
            query.order_by(SaaSAdminAuditEventModel.created_at.desc(), SaaSAdminAuditEventModel.id.desc())
            .offset(offset)
            .limit(safe_page_size)
            .all()
        )

        items = [
            {
                "id": row.id,
                "event_type": row.event_type,
                "client_ip": row.client_ip,
                "outcome": row.outcome,
                "deleted_keys": row.deleted_keys,
                "retry_after": row.retry_after,
                "reason": row.reason,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

        return {
            "items": items,
            "pagination": {
                "page": safe_page,
                "page_size": safe_page_size,
                "total": total,
            },
            "filters": {
                "from": start_date.isoformat() if start_date else None,
                "to": end_date.isoformat() if end_date else None,
                "outcome": normalized_outcome,
            },
        }

    def list_admin_audit_events_for_export(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        outcome: str | None = None,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        normalized_outcome = (outcome or "").strip().lower() or None
        safe_limit = min(20000, max(1, int(limit or 5000)))

        query = self.session.query(SaaSAdminAuditEventModel)

        start_dt = self._start_of_day(start_date)
        end_dt = self._end_of_day(end_date)
        if start_dt:
            query = query.filter(SaaSAdminAuditEventModel.created_at >= start_dt)
        if end_dt:
            query = query.filter(SaaSAdminAuditEventModel.created_at <= end_dt)
        if normalized_outcome:
            query = query.filter(SaaSAdminAuditEventModel.outcome == normalized_outcome)

        rows = (
            query.order_by(SaaSAdminAuditEventModel.created_at.desc(), SaaSAdminAuditEventModel.id.desc())
            .limit(safe_limit)
            .all()
        )

        return [
            {
                "id": row.id,
                "event_type": row.event_type,
                "client_ip": row.client_ip,
                "outcome": row.outcome,
                "deleted_keys": row.deleted_keys,
                "retry_after": row.retry_after,
                "reason": row.reason,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    def list_admin_audit_metric_operations(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        outcome: str | None = None,
        operation: str | None = None,
        request_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        normalized_outcome = (outcome or "").strip().lower() or None
        normalized_operation = (operation or "").strip().lower() or None
        normalized_request_id = (request_id or "").strip() or None

        safe_page = max(1, int(page or 1))
        safe_page_size = min(100, max(1, int(page_size or 20)))
        offset = (safe_page - 1) * safe_page_size

        query = self.session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation"
        )

        start_dt = self._start_of_day(start_date)
        end_dt = self._end_of_day(end_date)
        if start_dt:
            query = query.filter(SaaSAdminAuditEventModel.created_at >= start_dt)
        if end_dt:
            query = query.filter(SaaSAdminAuditEventModel.created_at <= end_dt)
        if normalized_outcome:
            query = query.filter(SaaSAdminAuditEventModel.outcome == normalized_outcome)
        if normalized_operation:
            query = query.filter(SaaSAdminAuditEventModel.reason.like(f"op={normalized_operation};%"))
        if normalized_request_id:
            query = query.filter(SaaSAdminAuditEventModel.reason.like(f"%rid={normalized_request_id[:24]}%"))

        total = int(query.count())
        rows = (
            query.order_by(SaaSAdminAuditEventModel.created_at.desc(), SaaSAdminAuditEventModel.id.desc())
            .offset(offset)
            .limit(safe_page_size)
            .all()
        )

        def _extract_reason_token(reason: str | None, prefix: str) -> str | None:
            if not reason:
                return None
            for part in reason.split(";"):
                if part.startswith(prefix):
                    return part[len(prefix):]
            return None

        items = []
        for row in rows:
            reason = row.reason or ""
            items.append(
                {
                    "id": row.id,
                    "event_type": row.event_type,
                    "client_ip": row.client_ip,
                    "outcome": row.outcome,
                    "processed_count": row.deleted_keys,
                    "operation": _extract_reason_token(reason, "op="),
                    "request_id": _extract_reason_token(reason, "rid="),
                    "reason": row.reason,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
            )

        return {
            "items": items,
            "pagination": {
                "page": safe_page,
                "page_size": safe_page_size,
                "total": total,
            },
            "filters": {
                "from": start_date.isoformat() if start_date else None,
                "to": end_date.isoformat() if end_date else None,
                "outcome": normalized_outcome,
                "operation": normalized_operation,
                "request_id": normalized_request_id,
            },
        }

    def list_admin_audit_metric_operations_for_export(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        outcome: str | None = None,
        operation: str | None = None,
        request_id: str | None = None,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        normalized_outcome = (outcome or "").strip().lower() or None
        normalized_operation = (operation or "").strip().lower() or None
        normalized_request_id = (request_id or "").strip() or None
        safe_limit = min(20000, max(1, int(limit or 5000)))

        query = self.session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation"
        )

        start_dt = self._start_of_day(start_date)
        end_dt = self._end_of_day(end_date)
        if start_dt:
            query = query.filter(SaaSAdminAuditEventModel.created_at >= start_dt)
        if end_dt:
            query = query.filter(SaaSAdminAuditEventModel.created_at <= end_dt)
        if normalized_outcome:
            query = query.filter(SaaSAdminAuditEventModel.outcome == normalized_outcome)
        if normalized_operation:
            query = query.filter(SaaSAdminAuditEventModel.reason.like(f"op={normalized_operation};%"))
        if normalized_request_id:
            query = query.filter(SaaSAdminAuditEventModel.reason.like(f"%rid={normalized_request_id[:24]}%"))

        rows = (
            query.order_by(SaaSAdminAuditEventModel.created_at.desc(), SaaSAdminAuditEventModel.id.desc())
            .limit(safe_limit)
            .all()
        )

        def _extract_reason_token(reason: str | None, prefix: str) -> str | None:
            if not reason:
                return None
            for part in reason.split(";"):
                if part.startswith(prefix):
                    return part[len(prefix):]
            return None

        return [
            {
                "id": row.id,
                "event_type": row.event_type,
                "client_ip": row.client_ip,
                "outcome": row.outcome,
                "processed_count": row.deleted_keys,
                "operation": _extract_reason_token(row.reason, "op="),
                "request_id": _extract_reason_token(row.reason, "rid="),
                "reason": row.reason,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    def get_admin_audit_metric_operations_metrics(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        operation: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        normalized_operation = (operation or "").strip().lower() or None
        normalized_request_id = (request_id or "").strip() or None

        query = self.session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation"
        )

        start_dt = self._start_of_day(start_date)
        end_dt = self._end_of_day(end_date)
        if start_dt:
            query = query.filter(SaaSAdminAuditEventModel.created_at >= start_dt)
        if end_dt:
            query = query.filter(SaaSAdminAuditEventModel.created_at <= end_dt)
        if normalized_operation:
            query = query.filter(SaaSAdminAuditEventModel.reason.like(f"op={normalized_operation};%"))
        if normalized_request_id:
            query = query.filter(SaaSAdminAuditEventModel.reason.like(f"%rid={normalized_request_id[:24]}%"))

        total_operations = int(query.count())

        by_outcome_rows = (
            query.with_entities(
                SaaSAdminAuditEventModel.outcome,
                func.count(SaaSAdminAuditEventModel.id),
            )
            .group_by(SaaSAdminAuditEventModel.outcome)
            .all()
        )
        by_outcome = {str(outcome): int(count) for outcome, count in by_outcome_rows}

        rows = query.order_by(SaaSAdminAuditEventModel.id.desc()).all()

        by_operation: dict[str, int] = {}
        total_processed = 0
        unique_request_ids: set[str] = set()

        for row in rows:
            reason = row.reason or ""
            op = None
            req = None
            for part in reason.split(";"):
                if part.startswith("op="):
                    op = part[len("op="):]
                elif part.startswith("rid="):
                    req = part[len("rid="):]

            if op:
                by_operation[op] = by_operation.get(op, 0) + 1
            if req and req != "-":
                unique_request_ids.add(req)
            total_processed += int(row.deleted_keys or 0)

        replay_count = int(by_outcome.get("replay", 0))
        dry_run_count = int(by_outcome.get("dry_run", 0))
        success_count = int(by_outcome.get("success", 0))

        replay_ratio = round(replay_count / total_operations, 4) if total_operations else 0.0

        return {
            "total_operations": total_operations,
            "by_outcome": by_outcome,
            "by_operation": by_operation,
            "success_count": success_count,
            "replay_count": replay_count,
            "dry_run_count": dry_run_count,
            "replay_ratio": replay_ratio,
            "total_processed": total_processed,
            "unique_request_ids": len(unique_request_ids),
            "filters": {
                "from": start_date.isoformat() if start_date else None,
                "to": end_date.isoformat() if end_date else None,
                "operation": normalized_operation,
                "request_id": normalized_request_id,
            },
        }

    def get_admin_audit_metrics(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        query = self.session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "cache_invalidate"
        )

        start_dt = self._start_of_day(start_date)
        end_dt = self._end_of_day(end_date)
        if start_dt:
            query = query.filter(SaaSAdminAuditEventModel.created_at >= start_dt)
        if end_dt:
            query = query.filter(SaaSAdminAuditEventModel.created_at <= end_dt)

        total_attempts = int(query.count())

        by_outcome_rows = (
            query.with_entities(
                SaaSAdminAuditEventModel.outcome,
                func.count(SaaSAdminAuditEventModel.id),
            )
            .group_by(SaaSAdminAuditEventModel.outcome)
            .all()
        )
        by_outcome = {str(outcome): int(count) for outcome, count in by_outcome_rows}

        top_ips_rows = (
            query.with_entities(
                SaaSAdminAuditEventModel.client_ip,
                func.count(SaaSAdminAuditEventModel.id).label("attempts"),
            )
            .group_by(SaaSAdminAuditEventModel.client_ip)
            .order_by(func.count(SaaSAdminAuditEventModel.id).desc())
            .limit(5)
            .all()
        )

        top_ips: list[dict[str, Any]] = []
        for ip, attempts in top_ips_rows:
            rate_limited = int(
                query.filter(
                    SaaSAdminAuditEventModel.client_ip == ip,
                    SaaSAdminAuditEventModel.outcome == "rate_limited",
                ).count()
            )
            top_ips.append(
                {
                    "client_ip": str(ip),
                    "attempts": int(attempts),
                    "rate_limited": rate_limited,
                }
            )

        rate_limited_count = int(by_outcome.get("rate_limited", 0))
        rate_limited_ratio = (
            round(rate_limited_count / total_attempts, 4)
            if total_attempts > 0
            else 0.0
        )

        return {
            "total_attempts": total_attempts,
            "by_outcome": by_outcome,
            "rate_limited": {
                "count": rate_limited_count,
                "ratio": rate_limited_ratio,
            },
            "top_ips": top_ips,
            "period": {
                "from": start_date.isoformat() if start_date else None,
                "to": end_date.isoformat() if end_date else None,
            },
        }

    def upsert_admin_audit_metrics_snapshot(
        self,
        snapshot_date: date,
        metrics: dict[str, Any],
        warning_threshold: float,
        critical_threshold: float,
        alert_status: str,
    ) -> dict[str, Any]:
        row: SaaSAuditMetricsSnapshotModel | None = (
            self.session.query(SaaSAuditMetricsSnapshotModel)
            .filter_by(snapshot_date=snapshot_date)
            .first()
        )

        total_attempts = int(metrics.get("total_attempts", 0) or 0)
        rate_limited_count = int(metrics.get("rate_limited", {}).get("count", 0) or 0)
        rate_limited_ratio = float(metrics.get("rate_limited", {}).get("ratio", 0.0) or 0.0)
        by_outcome = metrics.get("by_outcome", {})
        top_ips = metrics.get("top_ips", [])

        if row is None:
            row = SaaSAuditMetricsSnapshotModel(
                snapshot_date=snapshot_date,
                total_attempts=total_attempts,
                rate_limited_count=rate_limited_count,
                rate_limited_ratio=rate_limited_ratio,
                alert_status=alert_status,
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
                by_outcome_json=json.dumps(by_outcome, ensure_ascii=False),
                top_ips_json=json.dumps(top_ips, ensure_ascii=False),
            )
            self.session.add(row)
        else:
            row.total_attempts = total_attempts
            row.rate_limited_count = rate_limited_count
            row.rate_limited_ratio = rate_limited_ratio
            row.alert_status = alert_status
            row.warning_threshold = warning_threshold
            row.critical_threshold = critical_threshold
            row.by_outcome_json = json.dumps(by_outcome, ensure_ascii=False)
            row.top_ips_json = json.dumps(top_ips, ensure_ascii=False)

        self.session.commit()

        return {
            "snapshot_date": row.snapshot_date.isoformat(),
            "total_attempts": row.total_attempts,
            "rate_limited_count": row.rate_limited_count,
            "rate_limited_ratio": round(float(row.rate_limited_ratio or 0.0), 4),
            "alert_status": row.alert_status,
            "warning_threshold": round(float(row.warning_threshold or 0.0), 4),
            "critical_threshold": round(float(row.critical_threshold or 0.0), 4),
            "by_outcome": json.loads(row.by_outcome_json or "{}"),
            "top_ips": json.loads(row.top_ips_json or "[]"),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def list_admin_audit_metrics_snapshots(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        query = self.session.query(SaaSAuditMetricsSnapshotModel)
        if start_date:
            query = query.filter(SaaSAuditMetricsSnapshotModel.snapshot_date >= start_date)
        if end_date:
            query = query.filter(SaaSAuditMetricsSnapshotModel.snapshot_date <= end_date)

        rows = (
            query.order_by(SaaSAuditMetricsSnapshotModel.snapshot_date.desc())
            .all()
        )

        items = [
            {
                "snapshot_date": row.snapshot_date.isoformat() if row.snapshot_date else None,
                "total_attempts": row.total_attempts,
                "rate_limited_count": row.rate_limited_count,
                "rate_limited_ratio": round(float(row.rate_limited_ratio or 0.0), 4),
                "alert_status": row.alert_status,
                "warning_threshold": round(float(row.warning_threshold or 0.0), 4),
                "critical_threshold": round(float(row.critical_threshold or 0.0), 4),
                "by_outcome": json.loads(row.by_outcome_json or "{}"),
                "top_ips": json.loads(row.top_ips_json or "[]"),
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]

        return {
            "items": items,
            "period": {
                "from": start_date.isoformat() if start_date else None,
                "to": end_date.isoformat() if end_date else None,
            },
        }

    def get_latest_admin_audit_metrics_snapshot(self) -> dict[str, Any] | None:
        row: SaaSAuditMetricsSnapshotModel | None = (
            self.session.query(SaaSAuditMetricsSnapshotModel)
            .order_by(SaaSAuditMetricsSnapshotModel.snapshot_date.desc())
            .first()
        )
        if row is None:
            return None

        return {
            "snapshot_date": row.snapshot_date.isoformat() if row.snapshot_date else None,
            "total_attempts": row.total_attempts,
            "rate_limited_count": row.rate_limited_count,
            "rate_limited_ratio": round(float(row.rate_limited_ratio or 0.0), 4),
            "alert_status": row.alert_status,
            "warning_threshold": round(float(row.warning_threshold or 0.0), 4),
            "critical_threshold": round(float(row.critical_threshold or 0.0), 4),
            "by_outcome": json.loads(row.by_outcome_json or "{}"),
            "top_ips": json.loads(row.top_ips_json or "[]"),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def list_admin_audit_snapshot_dates(
        self,
        start_date: date,
        end_date: date,
    ) -> list[date]:
        rows = (
            self.session.query(SaaSAuditMetricsSnapshotModel.snapshot_date)
            .filter(SaaSAuditMetricsSnapshotModel.snapshot_date >= start_date)
            .filter(SaaSAuditMetricsSnapshotModel.snapshot_date <= end_date)
            .order_by(SaaSAuditMetricsSnapshotModel.snapshot_date.asc())
            .all()
        )
        return [row[0] for row in rows if row and row[0] is not None]

    @staticmethod
    def _stage_rank(stage: str | None) -> int:
        order = {
            "NEW": 1,
            "ENGAGED": 2,
            "RESERVATION_PENDING": 3,
            "RESERVATION_CONFIRMED": 4,
            "CHECKED_IN": 5,
        }
        return order.get((stage or "").upper(), 0)
