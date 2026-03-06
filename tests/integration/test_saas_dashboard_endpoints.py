from __future__ import annotations

import os
import uuid
from datetime import date, datetime

from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.cache.redis_repository import RedisRepository
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.models import AnalyticsEventModel, LeadModel, SaaSAdminAuditEventModel, SaaSAuditMetricsSnapshotModel
from app.infrastructure.persistence.sql.saas_repository_sql import SaaSRepositorySQL


def _unique_phone() -> str:
    return "5511888" + str(uuid.uuid4().int)[0:8]


def test_saas_kpis_endpoint_returns_expected_shape():
    session = SessionLocal()
    repo = SaaSRepositorySQL(session)
    client = TestClient(app)

    phone = _unique_phone()
    try:
        repo.touch_lead(phone=phone, source="twilio", stage="ENGAGED")
        repo.track_event(phone=phone, source="twilio", event_type="inbound_message")
        repo.track_event(
            phone=phone,
            source="twilio",
            event_type="outbound_message",
            success=True,
            response_time_ms=1200,
        )

        response = client.get("/saas/kpis")
        assert response.status_code == 200

        payload = response.json()
        assert "leads_captured" in payload
        assert "ai_response_rate" in payload
        assert "reservation_confirmation_rate" in payload
        assert "checkins_completed" in payload
        assert "avg_response_time_seconds" in payload
        assert "conversion_by_source" in payload
        assert "daily_series" in payload
        assert "series" in payload
        assert "granularity" in payload
        assert "period" in payload
        assert isinstance(payload["conversion_by_source"], dict)
        assert isinstance(payload["daily_series"], list)
        assert isinstance(payload["series"], list)
        assert len(payload["daily_series"]) >= 1
        assert "date" in payload["daily_series"][0]
    finally:
        session.query(AnalyticsEventModel).filter_by(phone_number=phone).delete()
        session.query(LeadModel).filter_by(phone_number=phone).delete()
        session.commit()
        session.close()


def test_saas_leads_and_funnel_reflect_seeded_lead_stage():
    session = SessionLocal()
    repo = SaaSRepositorySQL(session)
    client = TestClient(app)

    phone = _unique_phone()
    stage = "RESERVATION_CONFIRMED"

    try:
        repo.touch_lead(phone=phone, source="meta", stage=stage)
        repo.track_event(phone=phone, source="meta", event_type="inbound_message")

        leads_response = client.get(f"/saas/leads?status={stage}")
        assert leads_response.status_code == 200

        items = leads_response.json()["items"]
        assert any(item["phone_number"] == phone and item["stage"] == stage for item in items)

        funnel_response = client.get("/saas/funnel")
        assert funnel_response.status_code == 200

        stages = funnel_response.json()["stages"]
        confirmed_stage = next(item for item in stages if item["stage"] == stage)
        assert confirmed_stage["count"] >= 1
    finally:
        session.query(AnalyticsEventModel).filter_by(phone_number=phone).delete()
        session.query(LeadModel).filter_by(phone_number=phone).delete()
        session.commit()
        session.close()


def test_saas_funnel_journey_endpoint_returns_expected_shape():
    """Journey funnel: Lead → Reserva → Confirmada → Check-in → Check-out."""
    client = TestClient(app)
    response = client.get("/saas/funnel/journey")
    assert response.status_code == 200

    payload = response.json()
    assert "stages" in payload
    assert "total" in payload
    assert isinstance(payload["stages"], list)
    assert isinstance(payload["total"], int)

    expected_stages = ["LEAD", "RESERVA", "CONFIRMADA", "CHECK_IN", "CHECK_OUT"]
    stage_names = [s["stage"] for s in payload["stages"]]
    assert stage_names == expected_stages

    for s in payload["stages"]:
        assert "stage" in s
        assert "count" in s
        assert len(s["stage"]) > 0
        assert isinstance(s["count"], int)


def test_saas_kpis_filters_by_source_and_status():
    session = SessionLocal()
    repo = SaaSRepositorySQL(session)
    client = TestClient(app)

    phone_twilio = _unique_phone()
    phone_meta = _unique_phone()

    try:
        repo.touch_lead(phone=phone_twilio, source="twilio", stage="ENGAGED")
        repo.track_event(phone=phone_twilio, source="twilio", event_type="inbound_message")
        repo.track_event(phone=phone_twilio, source="twilio", event_type="outbound_message", success=True)

        repo.touch_lead(phone=phone_meta, source="meta", stage="NEW")
        repo.track_event(phone=phone_meta, source="meta", event_type="inbound_message")

        response = client.get("/saas/kpis?source=twilio&status=ENGAGED")
        assert response.status_code == 200
        payload = response.json()

        assert payload["period"]["source"] == "twilio"
        assert payload["period"]["status"] == "ENGAGED"
        assert payload["leads_captured"] >= 1
        assert set(payload["conversion_by_source"].keys()).issubset({"twilio"})
    finally:
        session.query(AnalyticsEventModel).filter(AnalyticsEventModel.phone_number.in_([phone_twilio, phone_meta])).delete(synchronize_session=False)
        session.query(LeadModel).filter(LeadModel.phone_number.in_([phone_twilio, phone_meta])).delete(synchronize_session=False)
        session.commit()
        session.close()


def test_saas_timeseries_endpoint_returns_points_with_requested_filters():
    session = SessionLocal()
    repo = SaaSRepositorySQL(session)
    client = TestClient(app)

    phone = _unique_phone()
    custom_source = "phase23test"

    try:
        repo.touch_lead(phone=phone, source=custom_source, stage="ENGAGED")
        repo.track_event(phone=phone, source=custom_source, event_type="inbound_message")
        repo.track_event(phone=phone, source=custom_source, event_type="outbound_message", success=True, response_time_ms=700)

        today = date.today().isoformat()
        response = client.get(
            f"/saas/timeseries?from={today}&to={today}&source={custom_source}&status=ENGAGED"
        )
        assert response.status_code == 200

        payload = response.json()
        assert payload["granularity"] == "day"
        assert payload["period"]["source"] == custom_source
        assert payload["period"]["status"] == "ENGAGED"
        assert isinstance(payload["points"], list)
        assert len(payload["points"]) == 1
        point = payload["points"][0]
        assert point["date"] == today
        assert "inbound_messages" in point
        assert "outbound_messages" in point
    finally:
        session.query(AnalyticsEventModel).filter_by(phone_number=phone).delete()
        session.query(LeadModel).filter_by(phone_number=phone).delete()
        session.commit()
        session.close()


def test_saas_kpis_compare_returns_current_previous_and_delta():
    session = SessionLocal()
    repo = SaaSRepositorySQL(session)
    client = TestClient(app)

    phone = _unique_phone()
    custom_source = "phase23compare"

    try:
        repo.touch_lead(phone=phone, source=custom_source, stage="ENGAGED")
        repo.track_event(phone=phone, source=custom_source, event_type="inbound_message")
        repo.track_event(phone=phone, source=custom_source, event_type="outbound_message", success=True, response_time_ms=500)

        today = date.today().isoformat()
        response = client.get(
            f"/saas/kpis/compare?from={today}&to={today}&source={custom_source}&status=ENGAGED"
        )
        assert response.status_code == 200

        payload = response.json()
        assert "current_period" in payload
        assert "previous_period" in payload
        assert "current" in payload
        assert "previous" in payload
        assert "delta" in payload
        assert "leads_captured" in payload["current"]
        assert "leads_captured" in payload["delta"]
        assert "absolute" in payload["delta"]["leads_captured"]
        assert "percent" in payload["delta"]["leads_captured"]
    finally:
        session.query(AnalyticsEventModel).filter_by(phone_number=phone).delete()
        session.query(LeadModel).filter_by(phone_number=phone).delete()
        session.commit()
        session.close()


def test_saas_timeseries_supports_week_and_month_granularity():
    client = TestClient(app)

    week_response = client.get("/saas/timeseries?granularity=week")
    assert week_response.status_code == 200
    week_payload = week_response.json()
    assert week_payload["granularity"] == "week"
    assert isinstance(week_payload["points"], list)

    month_response = client.get("/saas/timeseries?granularity=month")
    assert month_response.status_code == 200
    month_payload = month_response.json()
    assert month_payload["granularity"] == "month"
    assert isinstance(month_payload["points"], list)


def test_saas_kpis_compare_supports_granularity_series():
    client = TestClient(app)
    response = client.get("/saas/kpis/compare?granularity=week")
    assert response.status_code == 200
    payload = response.json()

    assert payload["granularity"] == "week"
    assert "series_current" in payload
    assert "series_previous" in payload
    assert isinstance(payload["series_current"], list)
    assert isinstance(payload["series_previous"], list)


def test_saas_kpis_supports_week_and_month_granularity():
    client = TestClient(app)

    week_response = client.get("/saas/kpis?granularity=week")
    assert week_response.status_code == 200
    week_payload = week_response.json()
    assert week_payload["granularity"] == "week"
    assert week_payload["period"]["granularity"] == "week"
    assert isinstance(week_payload["series"], list)

    month_response = client.get("/saas/kpis?granularity=month")
    assert month_response.status_code == 200
    month_payload = month_response.json()
    assert month_payload["granularity"] == "month"
    assert month_payload["period"]["granularity"] == "month"
    assert isinstance(month_payload["series"], list)


def test_saas_cache_invalidate_endpoint_removes_only_dashboard_keys():
    client = TestClient(app)
    cache = RedisRepository()

    dashboard_key = "saas:dashboard:phase28:test"
    other_key = "flow:phase28:test"

    cache.set(dashboard_key, {"k": "v"}, ttl_seconds=300)
    cache.set(other_key, {"step": "summary_displayed"}, ttl_seconds=300)

    try:
        previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
        os.environ["SAAS_ADMIN_TOKEN"] = "phase28-token"

        response = client.post(
            "/saas/cache/invalidate",
            headers={"X-Admin-Token": "phase28-token"},
        )
        assert response.status_code == 200

        payload = response.json()
        assert "deleted_keys" in payload
        assert payload["deleted_keys"] >= 1

        assert cache.get(dashboard_key) is None
        assert cache.get(other_key) is not None
    finally:
        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        cache.delete(dashboard_key)
        cache.delete(other_key)


def test_saas_cache_invalidate_returns_503_when_token_not_configured():
    client = TestClient(app)
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")

    try:
        os.environ.pop("SAAS_ADMIN_TOKEN", None)
        response = client.post(
            "/saas/cache/invalidate",
            headers={"X-Admin-Token": "anything"},
        )
        assert response.status_code == 503
    finally:
        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token


def test_saas_cache_invalidate_returns_401_without_header():
    client = TestClient(app)
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")

    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase29-token"
        response = client.post("/saas/cache/invalidate")
        assert response.status_code == 401
    finally:
        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token


def test_saas_cache_invalidate_returns_403_with_wrong_token():
    client = TestClient(app)
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")

    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase29-token"
        response = client.post(
            "/saas/cache/invalidate",
            headers={"X-Admin-Token": "wrong-token"},
        )
        assert response.status_code == 403
    finally:
        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token


def test_saas_cache_invalidate_rate_limit_returns_429_when_exceeded():
    client = TestClient(app)
    cache = RedisRepository()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_limit = os.environ.get("SAAS_CACHE_INVALIDATE_RATE_LIMIT")
    previous_window = os.environ.get("SAAS_CACHE_INVALIDATE_RATE_WINDOW_SECONDS")

    rl_key = "saas:cache_invalidate:rl:testclient"
    cache.delete(rl_key)

    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase210-token"
        os.environ["SAAS_CACHE_INVALIDATE_RATE_LIMIT"] = "2"
        os.environ["SAAS_CACHE_INVALIDATE_RATE_WINDOW_SECONDS"] = "60"

        first = client.post(
            "/saas/cache/invalidate",
            headers={"X-Admin-Token": "phase210-token"},
        )
        second = client.post(
            "/saas/cache/invalidate",
            headers={"X-Admin-Token": "phase210-token"},
        )
        third = client.post(
            "/saas/cache/invalidate",
            headers={"X-Admin-Token": "phase210-token"},
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert third.status_code == 429
        assert "Retry-After" in third.headers
    finally:
        cache.delete(rl_key)

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_limit is None:
            os.environ.pop("SAAS_CACHE_INVALIDATE_RATE_LIMIT", None)
        else:
            os.environ["SAAS_CACHE_INVALIDATE_RATE_LIMIT"] = previous_limit

        if previous_window is None:
            os.environ.pop("SAAS_CACHE_INVALIDATE_RATE_WINDOW_SECONDS", None)
        else:
            os.environ["SAAS_CACHE_INVALIDATE_RATE_WINDOW_SECONDS"] = previous_window


def test_saas_cache_invalidate_emits_audit_log(caplog):
    client = TestClient(app)
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_limit = os.environ.get("SAAS_CACHE_INVALIDATE_RATE_LIMIT")
    previous_window = os.environ.get("SAAS_CACHE_INVALIDATE_RATE_WINDOW_SECONDS")

    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase211-token"
        os.environ["SAAS_CACHE_INVALIDATE_RATE_LIMIT"] = "10"
        os.environ["SAAS_CACHE_INVALIDATE_RATE_WINDOW_SECONDS"] = "60"

        with caplog.at_level("INFO"):
            response = client.post(
                "/saas/cache/invalidate",
                headers={"X-Admin-Token": "phase211-token"},
            )

        assert response.status_code == 200
        assert any("saas_cache_invalidate_audit" in record.message for record in caplog.records)

        audit_record = next(record for record in caplog.records if "saas_cache_invalidate_audit" in record.message)
        assert getattr(audit_record, "outcome", None) == "success"
        assert getattr(audit_record, "client_ip", None) == "testclient"
    finally:
        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_limit is None:
            os.environ.pop("SAAS_CACHE_INVALIDATE_RATE_LIMIT", None)
        else:
            os.environ["SAAS_CACHE_INVALIDATE_RATE_LIMIT"] = previous_limit

        if previous_window is None:
            os.environ.pop("SAAS_CACHE_INVALIDATE_RATE_WINDOW_SECONDS", None)
        else:
            os.environ["SAAS_CACHE_INVALIDATE_RATE_WINDOW_SECONDS"] = previous_window


def test_saas_cache_invalidate_persists_audit_event_in_database():
    client = TestClient(app)
    cache = RedisRepository()
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_limit = os.environ.get("SAAS_CACHE_INVALIDATE_RATE_LIMIT")
    previous_window = os.environ.get("SAAS_CACHE_INVALIDATE_RATE_WINDOW_SECONDS")

    rl_key = "saas:cache_invalidate:rl:testclient"
    cache.delete(rl_key)

    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase212-token"
        os.environ["SAAS_CACHE_INVALIDATE_RATE_LIMIT"] = "10"
        os.environ["SAAS_CACHE_INVALIDATE_RATE_WINDOW_SECONDS"] = "60"

        response = client.post(
            "/saas/cache/invalidate",
            headers={"X-Admin-Token": "phase212-token"},
        )
        assert response.status_code == 200

        row = (
            session.query(SaaSAdminAuditEventModel)
            .filter_by(event_type="cache_invalidate", client_ip="testclient", outcome="success")
            .order_by(SaaSAdminAuditEventModel.id.desc())
            .first()
        )
        assert row is not None
        assert row.deleted_keys is not None
    finally:
        session.query(SaaSAdminAuditEventModel).filter_by(
            event_type="cache_invalidate",
            client_ip="testclient",
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        cache.delete(rl_key)

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_limit is None:
            os.environ.pop("SAAS_CACHE_INVALIDATE_RATE_LIMIT", None)
        else:
            os.environ["SAAS_CACHE_INVALIDATE_RATE_LIMIT"] = previous_limit

        if previous_window is None:
            os.environ.pop("SAAS_CACHE_INVALIDATE_RATE_WINDOW_SECONDS", None)
        else:
            os.environ["SAAS_CACHE_INVALIDATE_RATE_WINDOW_SECONDS"] = previous_window


def test_saas_audit_events_endpoint_returns_paginated_filtered_items():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")

    marker = "phase213-marker"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase213-token"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="cache_invalidate",
                client_ip="phase213-client",
                outcome="success",
                deleted_keys=3,
                reason=marker,
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="cache_invalidate",
                client_ip="phase213-client",
                outcome="rejected",
                reason=marker,
            )
        )
        session.commit()

        today = date.today().isoformat()
        response = client.get(
            f"/saas/audit-events?outcome=success&from={today}&to={today}&page=1&page_size=100",
            headers={"X-Admin-Token": "phase213-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert "items" in payload
        assert "pagination" in payload
        assert payload["pagination"]["page"] == 1
        assert payload["pagination"]["page_size"] == 100
        assert payload["filters"]["outcome"] == "success"
        assert all(item["outcome"] == "success" for item in payload["items"])
        assert any(item.get("reason") == marker for item in payload["items"])
    finally:
        session.query(SaaSAdminAuditEventModel).filter_by(reason=marker).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token


def test_saas_audit_events_export_returns_csv_with_filters():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")

    marker = "phase214-csv-marker"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase214-token"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="cache_invalidate",
                client_ip="phase214-client",
                outcome="success",
                deleted_keys=5,
                reason=marker,
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="cache_invalidate",
                client_ip="phase214-client",
                outcome="rejected",
                reason=marker,
            )
        )
        session.commit()

        today = date.today().isoformat()
        response = client.get(
            f"/saas/audit-events/export?outcome=success&from={today}&to={today}",
            headers={"X-Admin-Token": "phase214-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_events.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "id,event_type,client_ip,outcome,deleted_keys,retry_after,reason,created_at" in csv_text
        assert marker in csv_text
        assert ",success," in csv_text
        assert ",rejected," not in csv_text
    finally:
        session.query(SaaSAdminAuditEventModel).filter_by(reason=marker).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token


def test_saas_audit_events_metrics_returns_aggregated_values():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")

    marker = "phase215-metrics-marker"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase215-token"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="cache_invalidate",
                client_ip="10.0.0.1",
                outcome="success",
                deleted_keys=2,
                reason=marker,
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="cache_invalidate",
                client_ip="10.0.0.1",
                outcome="rate_limited",
                retry_after=20,
                reason=marker,
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="cache_invalidate",
                client_ip="10.0.0.2",
                outcome="rejected",
                reason=marker,
            )
        )
        session.commit()

        today = date.today().isoformat()
        response = client.get(
            f"/saas/audit-events/metrics?from={today}&to={today}",
            headers={"X-Admin-Token": "phase215-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["total_attempts"] >= 3
        assert payload["by_outcome"].get("success", 0) >= 1
        assert payload["by_outcome"].get("rate_limited", 0) >= 1
        assert payload["by_outcome"].get("rejected", 0) >= 1
        assert "rate_limited" in payload
        assert "ratio" in payload["rate_limited"]
        assert isinstance(payload["top_ips"], list)
        assert any(ip_row["client_ip"] == "10.0.0.1" for ip_row in payload["top_ips"])
    finally:
        session.query(SaaSAdminAuditEventModel).filter_by(reason=marker).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token


def test_saas_audit_events_metrics_returns_warning_when_ratio_exceeds_threshold():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_threshold = os.environ.get("SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD")
    previous_critical_threshold = os.environ.get("SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD")

    marker = "phase216-alert-marker"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase216-token"
        os.environ["SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD"] = "0.9"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="cache_invalidate",
                client_ip="10.1.0.1",
                outcome="rate_limited",
                retry_after=30,
                reason=marker,
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="cache_invalidate",
                client_ip="10.1.0.1",
                outcome="rate_limited",
                retry_after=15,
                reason=marker,
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="cache_invalidate",
                client_ip="10.1.0.1",
                outcome="success",
                deleted_keys=1,
                reason=marker,
            )
        )
        session.commit()

        today = date.today().isoformat()
        response = client.get(
            f"/saas/audit-events/metrics?from={today}&to={today}",
            headers={"X-Admin-Token": "phase216-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert "alert" in payload
        assert payload["alert"]["metric"] == "rate_limited_ratio"
        assert payload["alert"]["status"] == "warning"
        assert payload["alert"]["warning_threshold"] == 0.3
        assert payload["alert"]["critical_threshold"] == 0.9
    finally:
        session.query(SaaSAdminAuditEventModel).filter_by(reason=marker).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_threshold is None:
            os.environ.pop("SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD"] = previous_threshold

        if previous_critical_threshold is None:
            os.environ.pop("SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD"] = previous_critical_threshold


def test_saas_audit_events_metrics_returns_critical_when_ratio_exceeds_critical_threshold():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_threshold = os.environ.get("SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD")
    previous_critical_threshold = os.environ.get("SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD")

    marker = "phase217-critical-marker"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase217-token"
        os.environ["SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD"] = "0.2"
        os.environ["SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD"] = "0.5"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="cache_invalidate",
                client_ip="10.2.0.1",
                outcome="rate_limited",
                retry_after=20,
                reason=marker,
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="cache_invalidate",
                client_ip="10.2.0.1",
                outcome="rate_limited",
                retry_after=15,
                reason=marker,
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="cache_invalidate",
                client_ip="10.2.0.1",
                outcome="success",
                deleted_keys=1,
                reason=marker,
            )
        )
        session.commit()

        today = date.today().isoformat()
        response = client.get(
            f"/saas/audit-events/metrics?from={today}&to={today}",
            headers={"X-Admin-Token": "phase217-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["alert"]["status"] == "critical"
        assert payload["alert"]["warning_threshold"] == 0.2
        assert payload["alert"]["critical_threshold"] == 0.5
    finally:
        session.query(SaaSAdminAuditEventModel).filter_by(reason=marker).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_threshold is None:
            os.environ.pop("SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD"] = previous_threshold

        if previous_critical_threshold is None:
            os.environ.pop("SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD"] = previous_critical_threshold


def test_saas_audit_metrics_snapshot_create_and_history():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_threshold = os.environ.get("SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD")
    previous_critical_threshold = os.environ.get("SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD")

    marker = "phase218-snapshot-marker"
    today = date.today()
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase218-token"
        os.environ["SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="cache_invalidate",
                client_ip="10.3.0.1",
                outcome="rate_limited",
                retry_after=12,
                reason=marker,
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="cache_invalidate",
                client_ip="10.3.0.1",
                outcome="success",
                deleted_keys=1,
                reason=marker,
            )
        )
        session.commit()

        create_response = client.post(
            f"/saas/audit-events/metrics/snapshot?date={today.isoformat()}",
            headers={"X-Admin-Token": "phase218-token"},
        )
        assert create_response.status_code == 200
        create_payload = create_response.json()
        assert create_payload["snapshot"]["snapshot_date"] == today.isoformat()
        assert create_payload["snapshot"]["alert_status"] in {"healthy", "warning", "critical"}

        history_response = client.get(
            f"/saas/audit-events/metrics/history?from={today.isoformat()}&to={today.isoformat()}",
            headers={"X-Admin-Token": "phase218-token"},
        )
        assert history_response.status_code == 200
        history_payload = history_response.json()
        assert "items" in history_payload
        assert any(item["snapshot_date"] == today.isoformat() for item in history_payload["items"])
    finally:
        session.query(SaaSAuditMetricsSnapshotModel).filter_by(snapshot_date=today).delete(synchronize_session=False)
        session.query(SaaSAdminAuditEventModel).filter_by(reason=marker).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_threshold is None:
            os.environ.pop("SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD"] = previous_threshold

        if previous_critical_threshold is None:
            os.environ.pop("SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD"] = previous_critical_threshold


def test_saas_audit_metrics_status_returns_stale_and_freshness_metadata():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_max_age = os.environ.get("SAAS_AUDIT_SNAPSHOT_MAX_AGE_DAYS")

    stale_date = date(2026, 2, 28)
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase220-token"
        os.environ["SAAS_AUDIT_SNAPSHOT_MAX_AGE_DAYS"] = "1"

        session.query(SaaSAuditMetricsSnapshotModel).delete(synchronize_session=False)
        session.add(
            SaaSAuditMetricsSnapshotModel(
                snapshot_date=stale_date,
                total_attempts=10,
                rate_limited_count=3,
                rate_limited_ratio=0.3,
                alert_status="warning",
                warning_threshold=0.2,
                critical_threshold=0.5,
                by_outcome_json='{"success": 7, "rate_limited": 3}',
                top_ips_json='[{"client_ip": "10.4.0.1", "attempts": 10, "rate_limited": 3}]',
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/status",
            headers={"X-Admin-Token": "phase220-token"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "stale"
        assert payload["freshness"]["max_age_days"] == 1
        assert payload["freshness"]["age_days"] > 1
        assert payload["freshness"]["is_fresh"] is False
        assert payload["latest_snapshot"]["snapshot_date"] == stale_date.isoformat()
    finally:
        session.query(SaaSAuditMetricsSnapshotModel).filter_by(snapshot_date=stale_date).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_max_age is None:
            os.environ.pop("SAAS_AUDIT_SNAPSHOT_MAX_AGE_DAYS", None)
        else:
            os.environ["SAAS_AUDIT_SNAPSHOT_MAX_AGE_DAYS"] = previous_max_age


def test_saas_audit_metrics_backfill_creates_snapshot_range():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")

    from_day = date(2026, 3, 1)
    to_day = date(2026, 3, 2)
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase221-token"

        session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).delete(synchronize_session=False)
        session.commit()

        response = client.post(
            f"/saas/audit-events/metrics/backfill?from={from_day.isoformat()}&to={to_day.isoformat()}",
            headers={"X-Admin-Token": "phase221-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["created"] == 2
        assert payload["period"]["from"] == from_day.isoformat()
        assert payload["period"]["to"] == to_day.isoformat()
        assert len(payload["items"]) == 2

        stored = session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).count()
        assert stored == 2
    finally:
        session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token


def test_saas_audit_metrics_gaps_returns_missing_days_in_range():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")

    from_day = date(2026, 3, 1)
    middle_day = date(2026, 3, 2)
    to_day = date(2026, 3, 3)
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase222-token"

        session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).delete(synchronize_session=False)
        session.add(
            SaaSAuditMetricsSnapshotModel(
                snapshot_date=from_day,
                total_attempts=1,
                rate_limited_count=0,
                rate_limited_ratio=0.0,
                alert_status="healthy",
                warning_threshold=0.2,
                critical_threshold=0.5,
                by_outcome_json='{"success": 1}',
                top_ips_json='[]',
            )
        )
        session.add(
            SaaSAuditMetricsSnapshotModel(
                snapshot_date=to_day,
                total_attempts=1,
                rate_limited_count=0,
                rate_limited_ratio=0.0,
                alert_status="healthy",
                warning_threshold=0.2,
                critical_threshold=0.5,
                by_outcome_json='{"success": 1}',
                top_ips_json='[]',
            )
        )
        session.commit()

        response = client.get(
            f"/saas/audit-events/metrics/gaps?from={from_day.isoformat()}&to={to_day.isoformat()}",
            headers={"X-Admin-Token": "phase222-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["total_days"] == 3
        assert payload["present_days"] == 2
        assert payload["missing_count"] == 1
        assert payload["missing_dates"] == [middle_day.isoformat()]
    finally:
        session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token


def test_saas_audit_metrics_repair_fills_only_missing_days():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")

    from_day = date(2026, 3, 1)
    missing_day = date(2026, 3, 2)
    to_day = date(2026, 3, 3)
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase223-token"

        session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).delete(synchronize_session=False)
        session.add(
            SaaSAuditMetricsSnapshotModel(
                snapshot_date=from_day,
                total_attempts=2,
                rate_limited_count=0,
                rate_limited_ratio=0.0,
                alert_status="healthy",
                warning_threshold=0.2,
                critical_threshold=0.5,
                by_outcome_json='{"success": 2}',
                top_ips_json='[]',
            )
        )
        session.add(
            SaaSAuditMetricsSnapshotModel(
                snapshot_date=to_day,
                total_attempts=2,
                rate_limited_count=0,
                rate_limited_ratio=0.0,
                alert_status="healthy",
                warning_threshold=0.2,
                critical_threshold=0.5,
                by_outcome_json='{"success": 2}',
                top_ips_json='[]',
            )
        )
        session.commit()

        response = client.post(
            f"/saas/audit-events/metrics/repair?from={from_day.isoformat()}&to={to_day.isoformat()}",
            headers={"X-Admin-Token": "phase223-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["missing_before"] == 1
        assert payload["created"] == 1
        assert payload["created_dates"] == [missing_day.isoformat()]
        assert payload["missing_after"] == 0

        total_in_range = session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).count()
        assert total_in_range == 3
    finally:
        session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token


def test_saas_audit_metrics_repair_dry_run_does_not_create_snapshots():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")

    from_day = date(2026, 3, 1)
    missing_day = date(2026, 3, 2)
    to_day = date(2026, 3, 3)
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase224-token"

        session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).delete(synchronize_session=False)
        session.add(
            SaaSAuditMetricsSnapshotModel(
                snapshot_date=from_day,
                total_attempts=1,
                rate_limited_count=0,
                rate_limited_ratio=0.0,
                alert_status="healthy",
                warning_threshold=0.2,
                critical_threshold=0.5,
                by_outcome_json='{"success": 1}',
                top_ips_json='[]',
            )
        )
        session.add(
            SaaSAuditMetricsSnapshotModel(
                snapshot_date=to_day,
                total_attempts=1,
                rate_limited_count=0,
                rate_limited_ratio=0.0,
                alert_status="healthy",
                warning_threshold=0.2,
                critical_threshold=0.5,
                by_outcome_json='{"success": 1}',
                top_ips_json='[]',
            )
        )
        session.commit()

        response = client.post(
            f"/saas/audit-events/metrics/repair?from={from_day.isoformat()}&to={to_day.isoformat()}&dry_run=true",
            headers={"X-Admin-Token": "phase224-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["dry_run"] is True
        assert payload["missing_before"] == 1
        assert payload["planned"] == 1
        assert payload["planned_dates"] == [missing_day.isoformat()]
        assert payload["created"] == 0
        assert payload["missing_after"] == 1

        total_in_range = session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).count()
        assert total_in_range == 2
    finally:
        session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token


def test_saas_audit_metrics_gaps_rejects_too_large_range():
    client = TestClient(app)
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_max_range = os.environ.get("SAAS_AUDIT_SNAPSHOT_MAX_RANGE_DAYS")

    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase225-token"
        os.environ["SAAS_AUDIT_SNAPSHOT_MAX_RANGE_DAYS"] = "2"

        response = client.get(
            "/saas/audit-events/metrics/gaps?from=2026-03-01&to=2026-03-03",
            headers={"X-Admin-Token": "phase225-token"},
        )

        assert response.status_code == 422
        payload = response.json()
        assert "Date range too large" in payload.get("detail", "")
    finally:
        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_max_range is None:
            os.environ.pop("SAAS_AUDIT_SNAPSHOT_MAX_RANGE_DAYS", None)
        else:
            os.environ["SAAS_AUDIT_SNAPSHOT_MAX_RANGE_DAYS"] = previous_max_range


def test_saas_audit_metrics_backfill_supports_batch_size_metadata():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")

    from_day = date(2026, 3, 1)
    to_day = date(2026, 3, 3)
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase226-token"

        session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).delete(synchronize_session=False)
        session.commit()

        response = client.post(
            f"/saas/audit-events/metrics/backfill?from={from_day.isoformat()}&to={to_day.isoformat()}&batch_size=2",
            headers={"X-Admin-Token": "phase226-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["created"] == 3
        assert payload["batch_size"] == 2
        assert len(payload["batches"]) == 2
        assert payload["batches"][0]["created"] == 2
        assert payload["batches"][1]["created"] == 1

        stored = session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).count()
        assert stored == 3
    finally:
        session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token


def test_saas_audit_metrics_backfill_summary_only_omits_items_payload():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")

    from_day = date(2026, 3, 1)
    to_day = date(2026, 3, 3)
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase227-token"

        session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).delete(synchronize_session=False)
        session.commit()

        response = client.post(
            f"/saas/audit-events/metrics/backfill?from={from_day.isoformat()}&to={to_day.isoformat()}&batch_size=2&summary_only=true",
            headers={"X-Admin-Token": "phase227-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["summary_only"] is True
        assert payload["created"] == 3
        assert payload["omitted_items"] == 3
        assert "items" not in payload
        assert len(payload["batches"]) == 2
        assert "created_dates" not in payload["batches"][0]
    finally:
        session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token


def test_saas_audit_metrics_backfill_request_id_replay_is_idempotent():
    client = TestClient(app)
    session = SessionLocal()
    cache = RedisRepository()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_ttl = os.environ.get("SAAS_AUDIT_OPERATION_IDEMPOTENCY_TTL_SECONDS")

    from_day = date(2026, 3, 1)
    to_day = date(2026, 3, 3)
    request_id = "phase228-idempotent-1"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase228-token"
        os.environ["SAAS_AUDIT_OPERATION_IDEMPOTENCY_TTL_SECONDS"] = "300"

        session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).delete(synchronize_session=False)
        session.commit()

        for key in cache.client.scan_iter(match=f"saas:audit_ops:idempotency:backfill:{request_id}:*"):
            normalized = key.decode("utf-8") if isinstance(key, bytes) else str(key)
            cache.delete(normalized)

        first = client.post(
            f"/saas/audit-events/metrics/backfill?from={from_day.isoformat()}&to={to_day.isoformat()}&request_id={request_id}",
            headers={"X-Admin-Token": "phase228-token"},
        )
        second = client.post(
            f"/saas/audit-events/metrics/backfill?from={from_day.isoformat()}&to={to_day.isoformat()}&request_id={request_id}",
            headers={"X-Admin-Token": "phase228-token"},
        )

        assert first.status_code == 200
        assert second.status_code == 200

        first_payload = first.json()
        second_payload = second.json()
        assert first_payload["idempotent_replay"] is False
        assert second_payload["idempotent_replay"] is True
        assert first_payload["request_id"] == request_id
        assert second_payload["request_id"] == request_id
        assert second_payload["created"] == first_payload["created"]

        stored = session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).count()
        assert stored == 3
    finally:
        session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        for key in cache.client.scan_iter(match=f"saas:audit_ops:idempotency:backfill:{request_id}:*"):
            normalized = key.decode("utf-8") if isinstance(key, bytes) else str(key)
            cache.delete(normalized)

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_ttl is None:
            os.environ.pop("SAAS_AUDIT_OPERATION_IDEMPOTENCY_TTL_SECONDS", None)
        else:
            os.environ["SAAS_AUDIT_OPERATION_IDEMPOTENCY_TTL_SECONDS"] = previous_ttl


def test_saas_audit_metrics_backfill_replay_emits_operation_audit_events():
    client = TestClient(app)
    session = SessionLocal()
    cache = RedisRepository()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_ttl = os.environ.get("SAAS_AUDIT_OPERATION_IDEMPOTENCY_TTL_SECONDS")

    from_day = date(2026, 3, 1)
    to_day = date(2026, 3, 2)
    request_id = "phase229-audit-replay-id"
    marker = f"rid={request_id[:24]}"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase229-token"
        os.environ["SAAS_AUDIT_OPERATION_IDEMPOTENCY_TTL_SECONDS"] = "300"

        session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).delete(synchronize_session=False)
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like(f"%{marker}%"),
        ).delete(synchronize_session=False)
        session.commit()

        for key in cache.client.scan_iter(match=f"saas:audit_ops:idempotency:backfill:{request_id}:*"):
            normalized = key.decode("utf-8") if isinstance(key, bytes) else str(key)
            cache.delete(normalized)

        first = client.post(
            f"/saas/audit-events/metrics/backfill?from={from_day.isoformat()}&to={to_day.isoformat()}&request_id={request_id}",
            headers={"X-Admin-Token": "phase229-token"},
        )
        second = client.post(
            f"/saas/audit-events/metrics/backfill?from={from_day.isoformat()}&to={to_day.isoformat()}&request_id={request_id}",
            headers={"X-Admin-Token": "phase229-token"},
        )

        assert first.status_code == 200
        assert second.status_code == 200

        rows = session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like(f"%{marker}%"),
        ).all()
        outcomes = {row.outcome for row in rows}
        assert "success" in outcomes
        assert "replay" in outcomes
    finally:
        session.query(SaaSAuditMetricsSnapshotModel).filter(
            SaaSAuditMetricsSnapshotModel.snapshot_date >= from_day,
            SaaSAuditMetricsSnapshotModel.snapshot_date <= to_day,
        ).delete(synchronize_session=False)
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like(f"%{marker}%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        for key in cache.client.scan_iter(match=f"saas:audit_ops:idempotency:backfill:{request_id}:*"):
            normalized = key.decode("utf-8") if isinstance(key, bytes) else str(key)
            cache.delete(normalized)

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_ttl is None:
            os.environ.pop("SAAS_AUDIT_OPERATION_IDEMPOTENCY_TTL_SECONDS", None)
        else:
            os.environ["SAAS_AUDIT_OPERATION_IDEMPOTENCY_TTL_SECONDS"] = previous_ttl


def test_saas_audit_metric_operations_endpoint_lists_filtered_paginated_items():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")

    marker = "rid=phase230-op-list"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase230-token"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase230-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-02;b=2;s=0;d=0",
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase230-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-02;b=2;s=0;d=0",
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase230-client",
                outcome="dry_run",
                deleted_keys=0,
                reason="op=repair;rid=phase230-other;from=2026-03-01;to=2026-03-02;b=2;s=1;d=1",
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations"
            "?operation=backfill&request_id=phase230-op-list&page=1&page_size=10",
            headers={"X-Admin-Token": "phase230-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert "items" in payload
        assert "pagination" in payload
        assert payload["pagination"]["page"] == 1
        assert payload["filters"]["operation"] == "backfill"
        assert payload["filters"]["request_id"] == "phase230-op-list"
        assert len(payload["items"]) >= 2
        assert all(item["operation"] == "backfill" for item in payload["items"])
        assert all(item["request_id"] == "phase230-op-list" for item in payload["items"])
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase230-op-list%"),
        ).delete(synchronize_session=False)
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase230-other%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token


def test_saas_audit_metric_operations_export_returns_filtered_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")

    marker = "rid=phase231-csv"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase231-token"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase231-client",
                outcome="success",
                deleted_keys=3,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-03;b=2;s=1;d=0",
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase231-client",
                outcome="dry_run",
                deleted_keys=0,
                reason="op=repair;rid=phase231-other;from=2026-03-01;to=2026-03-03;b=2;s=1;d=1",
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/export"
            "?operation=backfill&request_id=phase231-csv",
            headers={"X-Admin-Token": "phase231-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "id,event_type,client_ip,outcome,processed_count,operation,request_id,reason,created_at" in csv_text
        assert "phase231-csv" in csv_text
        assert ",backfill," in csv_text
        assert "phase231-other" not in csv_text
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase231-csv%"),
        ).delete(synchronize_session=False)
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase231-other%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token


def test_saas_audit_metric_operations_metrics_returns_aggregated_values():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")

    marker = "rid=phase232-metrics"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase232-token"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase232-client",
                outcome="success",
                deleted_keys=3,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-03;b=2;s=0;d=0",
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase232-client",
                outcome="replay",
                deleted_keys=3,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-03;b=2;s=0;d=0",
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase232-client",
                outcome="dry_run",
                deleted_keys=0,
                reason="op=repair;rid=phase232-other;from=2026-03-01;to=2026-03-03;b=2;s=1;d=1",
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/metrics"
            "?operation=backfill&request_id=phase232-metrics",
            headers={"X-Admin-Token": "phase232-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["total_operations"] == 2
        assert payload["success_count"] == 1
        assert payload["replay_count"] == 1
        assert payload["dry_run_count"] == 0
        assert payload["total_processed"] == 6
        assert payload["by_operation"].get("backfill", 0) == 2
        assert payload["filters"]["operation"] == "backfill"
        assert payload["filters"]["request_id"] == "phase232-metrics"
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase232-metrics%"),
        ).delete(synchronize_session=False)
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase232-other%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token


def test_saas_audit_metric_operations_metrics_returns_alert_status():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase233-alert"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase233-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.6"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase233-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-03;b=2;s=0;d=0",
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase233-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-03;b=2;s=0;d=0",
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/metrics"
            "?operation=backfill&request_id=phase233-alert",
            headers={"X-Admin-Token": "phase233-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["replay_ratio"] == 0.5
        assert "alert" in payload
        assert payload["alert"]["metric"] == "operations_replay_ratio"
        assert payload["alert"]["warning_threshold"] == 0.3
        assert payload["alert"]["critical_threshold"] == 0.6
        assert payload["alert"]["status"] == "warning"
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase233-alert%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_returns_action_required_when_warning():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase234-status"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase234-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase234-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-03;b=2;s=0;d=0",
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase234-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-03;b=2;s=0;d=0",
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status"
            "?operation=backfill&request_id=phase234-status",
            headers={"X-Admin-Token": "phase234-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "warning"
        assert payload["action_required"] is True
        assert payload["alert"]["metric"] == "operations_replay_ratio"
        assert payload["metrics"]["replay_ratio"] == 0.5
        assert isinstance(payload["recommendations"], list)
        assert len(payload["recommendations"]) >= 1
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase234-status%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_history_returns_daily_statuses():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase235-history"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase235-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase235-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase235-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase235-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/history"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase235-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["period"]["from"] == "2026-03-01"
        assert payload["period"]["to"] == "2026-03-02"
        assert len(payload["items"]) == 2

        by_date = {item["date"]: item for item in payload["items"]}
        assert by_date["2026-03-01"]["status"] == "warning"
        assert by_date["2026-03-01"]["action_required"] is True
        assert by_date["2026-03-02"]["status"] == "healthy"
        assert by_date["2026-03-02"]["action_required"] is False

        assert payload["summary"]["days"] == 2
        assert payload["summary"]["by_status"]["warning"] == 1
        assert payload["summary"]["by_status"]["healthy"] == 1
        assert payload["summary"]["action_required_days"] == 1
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase235-history%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_history_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase236-history-export"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase236-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase236-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase236-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase236-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/history/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase236-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_history.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "date,status,action_required,total_operations,replay_count,replay_ratio,dry_run_count,success_count,total_processed,unique_request_ids,warning_threshold,critical_threshold" in csv_text
        assert "2026-03-01,warning,true" in csv_text
        assert "2026-03-02,healthy,false" in csv_text
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase236-history-export%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_history_compare_returns_delta():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase237-history-compare"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase237-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase237-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase237-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase237-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase237-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase237-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/history/compare"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase237-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["current_period"]["from"] == "2026-03-01"
        assert payload["current_period"]["to"] == "2026-03-02"
        assert payload["previous_period"]["from"] == "2026-02-27"
        assert payload["previous_period"]["to"] == "2026-02-28"

        assert payload["current_period"]["summary"]["by_status"]["warning"] == 1
        assert payload["current_period"]["summary"]["action_required_days"] == 1
        assert payload["previous_period"]["summary"]["by_status"]["healthy"] == 2
        assert payload["previous_period"]["summary"]["action_required_days"] == 0

        assert payload["delta"]["action_required_days"] == 1
        assert payload["delta"]["warning_days"] == 1
        assert payload["delta"]["critical_days"] == 0
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase237-history-compare%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_history_compare_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase238-history-compare-export"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase238-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase238-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase238-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase238-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase238-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase238-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/history/compare/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase238-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_history_compare.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "current_from,current_to,previous_from,previous_to,operation,current_days,current_healthy_days,current_warning_days,current_critical_days,current_action_required_days,previous_days,previous_healthy_days,previous_warning_days,previous_critical_days,previous_action_required_days,delta_action_required_days,delta_warning_days,delta_critical_days" in csv_text
        assert "2026-03-01,2026-03-02,2026-02-27,2026-02-28,backfill,2,1,1,0,1,2,2,0,0,0,1,1,0" in csv_text
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase238-history-compare-export%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_returns_worsening_with_action_required():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase239-status-trend"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase239-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase239-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase239-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase239-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase239-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase239-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase239-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["trend"] == "worsening"
        assert payload["action_required"] is True
        assert payload["delta"]["action_required_days"] == 1
        assert payload["delta"]["warning_days"] == 1
        assert payload["delta"]["critical_days"] == 0
        assert isinstance(payload["recommendations"], list)
        assert len(payload["recommendations"]) >= 1
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase239-status-trend%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase240-status-trend-export"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase240-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase240-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase240-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase240-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase240-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase240-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase240-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "current_from,current_to,previous_from,previous_to,operation,trend,action_required,delta_action_required_days,delta_warning_days,delta_critical_days,recommendations" in csv_text
        assert "2026-03-01,2026-03-02,2026-02-27,2026-02-28,backfill,worsening,true,1,1,0," in csv_text
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase240-status-trend-export%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_status_returns_warning_with_action_required():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase241-status-trend-status"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase241-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase241-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase241-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase241-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase241-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase241-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/status"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase241-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["trend"] == "worsening"
        assert payload["status"] == "warning"
        assert payload["action_required"] is True
        assert payload["alert"]["metric"] == "operations_status_trend"
        assert payload["alert"]["status"] == "warning"
        assert payload["delta"]["action_required_days"] == 1
        assert payload["delta"]["critical_days"] == 0
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase241-status-trend-status%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_status_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase242-status-trend-status-export"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase242-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase242-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase242-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase242-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase242-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase242-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/status/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase242-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_status.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "current_from,current_to,previous_from,previous_to,operation,status,trend,action_required,current_action_required_days,current_critical_days,delta_action_required_days,delta_warning_days,delta_critical_days,recommendations" in csv_text
        assert "2026-03-01,2026-03-02,2026-02-27,2026-02-28,backfill,warning,worsening,true,1,0,1,1,0," in csv_text
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase242-status-trend-status-export%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_returns_priority_and_headline():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase243-status-trend-overview"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase243-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase243-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase243-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase243-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase243-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase243-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase243-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
        assert payload["action_required"] is True
        assert isinstance(payload["headline"], str)
        assert payload["headline"]
        assert payload["snapshot"]["delta_action_required_days"] == 1
        assert payload["snapshot"]["delta_warning_days"] == 1
        assert payload["snapshot"]["delta_critical_days"] == 0
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase243-status-trend-overview%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase244-status-trend-overview-export"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase244-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase244-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase244-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase244-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase244-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase244-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase244-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "current_from,current_to,previous_from,previous_to,operation,status,trend,priority,headline,action_required,current_action_required_days,current_critical_days,delta_action_required_days,delta_warning_days,delta_critical_days,next_check_in_minutes" in csv_text
        assert "2026-03-01,2026-03-02,2026-02-27,2026-02-28,backfill,warning,worsening,medium," in csv_text
        assert ",true,1,0,1,1,0," in csv_text
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase244-status-trend-overview-export%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_returns_compact_payload():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase245-status-trend-overview-brief"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase245-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase245-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase245-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase245-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase245-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase245-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase245-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
        assert payload["action_required"] is True
        assert payload["operation"] == "backfill"
        assert payload["period"]["from"] == "2026-03-01"
        assert payload["period"]["to"] == "2026-03-02"
        assert payload["snapshot"]["delta_action_required_days"] == 1
        assert payload["snapshot"]["delta_warning_days"] == 1
        assert payload["snapshot"]["delta_critical_days"] == 0
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase245-status-trend-overview-brief%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase246-status-trend-overview-brief-export"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase246-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase246-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase246-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase246-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase246-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase246-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase246-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "current_from,current_to,operation,status,trend,priority,headline,action_required,current_action_required_days,current_critical_days,delta_action_required_days,delta_warning_days,delta_critical_days,next_check_in_minutes" in csv_text
        assert "2026-03-01,2026-03-02,backfill,warning,worsening,medium," in csv_text
        assert ",true,1,0,1,1,0," in csv_text
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase246-status-trend-overview-brief-export%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_returns_directive():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase247-status-trend-overview-brief-decision"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase247-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase247-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase247-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase247-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase247-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase247-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase247-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
        assert payload["decision"] == "investigate"
        assert payload["action_required"] is True
        assert payload["operation"] == "backfill"
        assert payload["period"]["from"] == "2026-03-01"
        assert payload["period"]["to"] == "2026-03-02"
        assert payload["snapshot"]["delta_action_required_days"] == 1
        assert payload["snapshot"]["delta_warning_days"] == 1
        assert payload["snapshot"]["delta_critical_days"] == 0
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase247-status-trend-overview-brief-decision%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase248-status-trend-overview-brief-decision-export"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase248-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase248-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase248-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase248-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase248-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase248-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase248-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief_decision.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "current_from,current_to,operation,status,trend,priority,decision,reason,action_required,current_action_required_days,current_critical_days,delta_action_required_days,delta_warning_days,delta_critical_days,next_check_in_minutes" in csv_text
        assert "2026-03-01,2026-03-02,backfill,warning,worsening,medium,investigate," in csv_text
        assert ",true,1,0,1,1,0," in csv_text
    finally:
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase248-status-trend-overview-brief-decision-export%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_returns_compact_alert_message():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase249-status-trend-overview-brief-decision-notice"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase249-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase249-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase249-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase249-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase249-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase249-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase249-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
        assert payload["decision"] == "investigate"
        assert payload["action_required"] is True
        assert payload["operation"] == "backfill"
        assert payload["period"]["from"] == "2026-03-01"
        assert payload["period"]["to"] == "2026-03-02"
        assert "Investigar" in payload["title"]
        assert "Risco moderado" in payload["message"]
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase249-status-trend-overview-brief-decision-notice%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase250-status-trend-overview-brief-decision-notice-export"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase250-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase250-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase250-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase250-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase250-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase250-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase250-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief_decision_notice.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "current_from,current_to,operation,status,trend,priority,decision,title,message,action_required,next_check_in_minutes" in csv_text
        assert "2026-03-01,2026-03-02,backfill,warning,worsening,medium,investigate,Investigar piora de tendência," in csv_text
        assert ",true," in csv_text
    finally:
        client.close()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_returns_ready_payload():
    client = TestClient(app)
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase251-token"

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase251-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["channel"] in {"incident", "ops-alert", "ops-monitor"}
        assert payload["status"] in {"healthy", "warning", "critical"}
        assert payload["trend"] in {"improving", "stable", "worsening"}
        assert payload["priority"] in {"low", "medium", "high"}
        assert payload["decision"] in {"monitor", "investigate", "escalate"}
        assert isinstance(payload["action_required"], bool)
        assert payload["operation"] == "backfill"
        assert payload["period"]["from"] == "2026-03-01"
        assert payload["period"]["to"] == "2026-03-02"
        assert payload["dedupe_key"].startswith("ops-trend-notice:backfill:2026-03-01:2026-03-02:")
        assert payload["title"]
        assert payload["message"]
    finally:
        client.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase252-dispatch-export"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase252-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase252-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase252-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase252-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase252-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase252-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase252-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "channel,dedupe_key,title,message,status,trend,priority,decision,action_required,operation,period_from,period_to,next_check_in_minutes" in csv_text
        assert "ops-alert,ops-trend-notice:backfill:2026-03-01:2026-03-02:warning:investigate,Investigar piora de tendência," in csv_text
        assert ",warning,worsening,medium,investigate,true,backfill,2026-03-01,2026-03-02," in csv_text
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase252-status-trend-overview-brief-decision-notice-dispatch-export%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_returns_targets():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase253-routes"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase253-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase253-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase253-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase253-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase253-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase253-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase253-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["channel"] == "ops-alert"
        assert payload["targets"] == ["oncall-ops"]
        assert payload["fallback_channel"] == "ops-monitor"
        assert payload["fallback_targets"] == ["ops-daily"]
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
        assert payload["action_required"] is True
        assert payload["operation"] == "backfill"
        assert payload["dedupe_key"].startswith("ops-trend-notice:backfill:2026-03-01:2026-03-02:warning:ops-alert")
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase253-routes%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=phase254-routes-export"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase254-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase254-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase254-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase254-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase254-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase254-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase254-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "channel,targets,fallback_channel,fallback_targets,dedupe_key,status,trend,priority,action_required,operation,period_from,period_to,next_check_in_minutes" in csv_text
        assert "ops-alert,oncall-ops,ops-monitor,ops-daily,ops-trend-notice:backfill:2026-03-01:2026-03-02:warning:ops-alert,warning,worsening,medium,true,backfill,2026-03-01,2026-03-02," in csv_text
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%phase254-routes-export%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_returns_compact_targets():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph255r"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase255-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase255-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase255-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase255-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase255-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase255-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase255-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["channel"] == "ops-alert"
        assert payload["primary_target"] == "oncall-ops"
        assert payload["fallback_target"] == "ops-daily"
        assert payload["targets_count"] >= 1
        assert payload["fallback_targets_count"] >= 1
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
        assert payload["action_required"] is True
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph255r%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph256rb"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase256-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase256-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase256-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase256-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase256-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase256-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase256-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "channel,primary_target,fallback_target,targets_count,fallback_targets_count,status,trend,priority,action_required,operation,period_from,period_to,next_check_in_minutes" in csv_text
        assert "ops-alert,oncall-ops,ops-daily,1,1,warning,worsening,medium,true,backfill,2026-03-01,2026-03-02," in csv_text
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph256rb%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_returns_route_decision():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph257rd"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase257-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase257-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase257-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase257-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase257-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase257-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase257-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["route_decision"] == "dispatch_primary"
        assert payload["channel"] == "ops-alert"
        assert payload["primary_target"] == "oncall-ops"
        assert payload["fallback_target"] == "ops-daily"
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
        assert payload["action_required"] is True
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph257rd%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph258de"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase258-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase258-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase258-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase258-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase258-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase258-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase258-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "route_decision,channel,primary_target,fallback_target,status,trend,priority,action_required,operation,period_from,period_to,next_check_in_minutes" in csv_text
        assert "dispatch_primary,ops-alert,oncall-ops,ops-daily,warning,worsening,medium,true,backfill,2026-03-01,2026-03-02," in csv_text
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph258de%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_returns_checklist():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph259rbk"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase259-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase259-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase259-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase259-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase259-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase259-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase259-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["route_decision"] == "dispatch_primary"
        assert payload["channel"] == "ops-alert"
        assert payload["primary_target"] == "oncall-ops"
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
        assert payload["action_required"] is True
        assert isinstance(payload["checklist"], list)
        assert len(payload["checklist"]) >= 2
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph259rbk%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph260rbkexp"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase260-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase260-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase260-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase260-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase260-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase260-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase260-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "route_decision,channel,primary_target,status,trend,priority,action_required,operation,period_from,period_to,next_check_in_minutes,checklist" in csv_text
        assert "dispatch_primary,ops-alert,oncall-ops,warning,worsening,medium,true,backfill,2026-03-01,2026-03-02," in csv_text
        assert "Notificar on-call operacional no canal primário." in csv_text
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph260rbkexp%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_returns_json():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph261rbkasg"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase261-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase261-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase261-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase261-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase261-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase261-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase261-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["route_decision"] == "dispatch_primary"
        assert payload["channel"] == "ops-alert"
        assert payload["primary_target"] == "oncall-ops"
        assert payload["owner"] == "oncall-ops"
        assert payload["escalation_target"] == "ops-manager"
        assert payload["ack_required"] is True
        assert payload["ack_deadline_minutes"] == 30
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
        assert payload["checklist_size"] >= 2
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph261rbkasg%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph262rbkasgexp"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase262-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase262-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase262-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase262-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase262-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase262-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase262-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "route_decision,channel,primary_target,owner,escalation_target,ack_required,ack_deadline_minutes,status,trend,priority,checklist_size,operation,period_from,period_to,next_check_in_minutes" in csv_text
        assert "dispatch_primary,ops-alert,oncall-ops,oncall-ops,ops-manager,true,30,warning,worsening,medium,3,backfill,2026-03-01,2026-03-02," in csv_text
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph262rbkasgexp%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_returns_json():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph263rbkqueue"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase263-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase263-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase263-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase263-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase263-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase263-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase263-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["queue_name"] == "ops-action-required"
        assert payload["queue_priority"] == "p2"
        assert payload["owner"] == "oncall-ops"
        assert payload["escalation_target"] == "ops-manager"
        assert payload["ack_required"] is True
        assert payload["ack_deadline_minutes"] == 30
        assert payload["route_decision"] == "dispatch_primary"
        assert payload["priority"] == "medium"
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph263rbkqueue%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph264rbkqexp"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase264-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase264-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase264-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase264-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase264-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase264-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase264-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "queue_name,queue_priority,owner,escalation_target,ack_required,ack_deadline_minutes,route_decision,channel,primary_target,status,trend,priority,operation,period_from,period_to,next_check_in_minutes" in csv_text
        assert "ops-action-required,p2,oncall-ops,ops-manager,true,30,dispatch_primary,ops-alert,oncall-ops,warning,worsening,medium,backfill,2026-03-01,2026-03-02," in csv_text
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph264rbkqexp%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_returns_json():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph265rbkqticket"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase265-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase265-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase265-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase265-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase265-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase265-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase265-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["ticket_type"] == "incident"
        assert payload["ticket_state"] == "open"
        assert payload["ticket_severity"] == "sev2"
        assert payload["queue_name"] == "ops-action-required"
        assert payload["queue_priority"] == "p2"
        assert payload["owner"] == "oncall-ops"
        assert payload["escalation_target"] == "ops-manager"
        assert payload["ack_required"] is True
        assert payload["ack_deadline_minutes"] == 30
        assert payload["route_decision"] == "dispatch_primary"
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph265rbkqticket%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph266rbkqticketexp"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase266-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase266-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase266-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase266-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase266-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase266-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase266-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "ticket_type,ticket_state,ticket_severity,queue_name,queue_priority,owner,escalation_target,ack_required,ack_deadline_minutes,route_decision,channel,primary_target,status,trend,priority,operation,period_from,period_to,next_check_in_minutes" in csv_text
        assert "incident,open,sev2,ops-action-required,p2,oncall-ops,ops-manager,true,30,dispatch_primary,ops-alert,oncall-ops,warning,worsening,medium,backfill,2026-03-01,2026-03-02," in csv_text
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph266rbkqticketexp%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_returns_json():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph267rbkqsla"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase267-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase267-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase267-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase267-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase267-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase267-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase267-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["ticket_type"] == "incident"
        assert payload["ticket_state"] == "open"
        assert payload["ticket_severity"] == "sev2"
        assert payload["queue_name"] == "ops-action-required"
        assert payload["queue_priority"] == "p2"
        assert payload["ack_required"] is True
        assert payload["ack_deadline_minutes"] == 30
        assert payload["sla_status"] == "on_track"
        assert payload["breach_risk"] == "medium"
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph267rbkqsla%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph268rbkqslaexp"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase268-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase268-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase268-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase268-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase268-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase268-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase268-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "ticket_type,ticket_state,ticket_severity,queue_name,queue_priority,owner,escalation_target,ack_required,ack_deadline_minutes,sla_status,breach_risk,route_decision,status,trend,priority,operation,period_from,period_to,next_check_in_minutes" in csv_text
        assert "incident,open,sev2,ops-action-required,p2,oncall-ops,ops-manager,true,30,on_track,medium,dispatch_primary,warning,worsening,medium,backfill,2026-03-01,2026-03-02," in csv_text
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph268rbkqslaexp%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_returns_json():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph269rbkqslawatch"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase269-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase269-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase269-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase269-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase269-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase269-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase269-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["watch_state"] == "attention"
        assert payload["should_page"] is True
        assert payload["sla_status"] == "on_track"
        assert payload["breach_risk"] == "medium"
        assert payload["ticket_type"] == "incident"
        assert payload["ticket_state"] == "open"
        assert payload["ticket_severity"] == "sev2"
        assert payload["queue_name"] == "ops-action-required"
        assert payload["queue_priority"] == "p2"
        assert payload["ack_required"] is True
        assert payload["ack_deadline_minutes"] == 30
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph269rbkqslawatch%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph270rbkqslawatchexp"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase270-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase270-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase270-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase270-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase270-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase270-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase270-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "watch_state,should_page,sla_status,breach_risk,ticket_type,ticket_state,ticket_severity,queue_name,queue_priority,owner,ack_required,ack_deadline_minutes,status,trend,priority,operation,period_from,period_to,next_check_in_minutes" in csv_text
        assert "attention,true,on_track,medium,incident,open,sev2,ops-action-required,p2,oncall-ops,true,30,warning,worsening,medium,backfill,2026-03-01,2026-03-02," in csv_text
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph270rbkqslawatchexp%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_returns_json():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph271rbkqslasum"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase271-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase271-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase271-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase271-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase271-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase271-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase271-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["watch_state"] == "attention"
        assert payload["should_page"] is True
        assert payload["escalation_mode"] == "expedited"
        assert payload["follow_up_in_minutes"] == 15
        assert payload["sla_status"] == "on_track"
        assert payload["breach_risk"] == "medium"
        assert payload["ticket_type"] == "incident"
        assert payload["ticket_state"] == "open"
        assert payload["ticket_severity"] == "sev2"
        assert payload["queue_name"] == "ops-action-required"
        assert payload["queue_priority"] == "p2"
        assert payload["ack_required"] is True
        assert payload["ack_deadline_minutes"] == 30
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph271rbkqslasum%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph272rbkqslasumexp"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase272-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase272-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase272-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase272-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase272-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase272-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase272-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "watch_state,should_page,escalation_mode,follow_up_in_minutes,sla_status,breach_risk,ticket_type,ticket_state,ticket_severity,queue_name,queue_priority,owner,ack_required,ack_deadline_minutes,status,trend,priority,operation,period_from,period_to,next_check_in_minutes" in csv_text
        assert "attention,true,expedited,15,on_track,medium,incident,open,sev2,ops-action-required,p2,oncall-ops,true,30,warning,worsening,medium,backfill,2026-03-01,2026-03-02," in csv_text
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph272rbkqslasumexp%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_returns_json():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph273rbkqsladec"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase273-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase273-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase273-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase273-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase273-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase273-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase273-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["decision"] == "escalate_follow_up"
        assert payload["action"] == "page_and_follow_up"
        assert payload["watch_state"] == "attention"
        assert payload["should_page"] is True
        assert payload["escalation_mode"] == "expedited"
        assert payload["follow_up_in_minutes"] == 15
        assert payload["sla_status"] == "on_track"
        assert payload["breach_risk"] == "medium"
        assert payload["ticket_type"] == "incident"
        assert payload["ticket_state"] == "open"
        assert payload["ticket_severity"] == "sev2"
        assert payload["queue_name"] == "ops-action-required"
        assert payload["queue_priority"] == "p2"
        assert payload["ack_required"] is True
        assert payload["ack_deadline_minutes"] == 30
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph273rbkqsladec%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph274rbkqsladecexp"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase274-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase274-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase274-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase274-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase274-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase274-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase274-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "decision,action,watch_state,should_page,escalation_mode,follow_up_in_minutes,sla_status,breach_risk,ticket_type,ticket_state,ticket_severity,queue_name,queue_priority,owner,ack_required,ack_deadline_minutes,status,trend,priority,operation,period_from,period_to,next_check_in_minutes" in csv_text
        assert "escalate_follow_up,page_and_follow_up,attention,true,expedited,15,on_track,medium,incident,open,sev2,ops-action-required,p2,oncall-ops,true,30,warning,worsening,medium,backfill,2026-03-01,2026-03-02," in csv_text
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph274rbkqsladecexp%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch_returns_json():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph275rbkqsladispatch"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase275-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase275-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase275-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase275-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase275-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase275-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase275-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["dispatch_mode"] == "on-call"
        assert payload["notify_channel"] == "ops-alert"
        assert payload["decision"] == "escalate_follow_up"
        assert payload["action"] == "page_and_follow_up"
        assert payload["watch_state"] == "attention"
        assert payload["should_page"] is True
        assert payload["escalation_mode"] == "expedited"
        assert payload["follow_up_in_minutes"] == 15
        assert payload["sla_status"] == "on_track"
        assert payload["breach_risk"] == "medium"
        assert payload["ticket_type"] == "incident"
        assert payload["ticket_state"] == "open"
        assert payload["ticket_severity"] == "sev2"
        assert payload["queue_name"] == "ops-action-required"
        assert payload["queue_priority"] == "p2"
        assert payload["ack_required"] is True
        assert payload["ack_deadline_minutes"] == 30
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph275rbkqsladispatch%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph276rbkqsladispatchexp"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase276-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase276-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase276-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase276-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase276-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase276-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase276-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "dispatch_mode,notify_channel,decision,action,watch_state,should_page,escalation_mode,follow_up_in_minutes,sla_status,breach_risk,ticket_type,ticket_state,ticket_severity,queue_name,queue_priority,owner,ack_required,ack_deadline_minutes,status,trend,priority,operation,period_from,period_to,next_check_in_minutes" in csv_text
        assert "on-call,ops-alert,escalate_follow_up,page_and_follow_up,attention,true,expedited,15,on_track,medium,incident,open,sev2,ops-action-required,p2,oncall-ops,true,30,warning,worsening,medium,backfill,2026-03-01,2026-03-02," in csv_text
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph276rbkqsladispatchexp%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch_receipt_returns_json():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph277rbkqslareceipt"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase277-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase277-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase277-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase277-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase277-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase277-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/receipt"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase277-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["receipt_status"] == "sent_priority"
        assert payload["dispatch_mode"] == "on-call"
        assert payload["notify_channel"] == "ops-alert"
        assert payload["decision"] == "escalate_follow_up"
        assert payload["action"] == "page_and_follow_up"
        assert payload["watch_state"] == "attention"
        assert payload["should_page"] is True
        assert payload["escalation_mode"] == "expedited"
        assert payload["follow_up_in_minutes"] == 15
        assert payload["sla_status"] == "on_track"
        assert payload["breach_risk"] == "medium"
        assert payload["ticket_type"] == "incident"
        assert payload["ticket_state"] == "open"
        assert payload["ticket_severity"] == "sev2"
        assert payload["queue_name"] == "ops-action-required"
        assert payload["queue_priority"] == "p2"
        assert payload["ack_required"] is True
        assert payload["ack_deadline_minutes"] == 30
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph277rbkqslareceipt%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch_receipt_export_returns_csv():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph278rbkqslareceiptexp"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase278-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase278-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase278-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase278-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase278-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase278-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/receipt/export"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase278-token"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch_receipt.csv\"" in response.headers.get("content-disposition", "")

        csv_text = response.text
        assert "receipt_status,dispatch_mode,notify_channel,decision,action,watch_state,should_page,escalation_mode,follow_up_in_minutes,sla_status,breach_risk,ticket_type,ticket_state,ticket_severity,queue_name,queue_priority,owner,ack_required,ack_deadline_minutes,status,trend,priority,operation,period_from,period_to,next_check_in_minutes" in csv_text
        assert "sent_priority,on-call,ops-alert,escalate_follow_up,page_and_follow_up,attention,true,expedited,15,on_track,medium,incident,open,sev2,ops-action-required,p2,oncall-ops,true,30,warning,worsening,medium,backfill,2026-03-01,2026-03-02," in csv_text
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph278rbkqslareceiptexp%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical


def test_saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch_receipt_review_returns_json():
    client = TestClient(app)
    session = SessionLocal()
    previous_token = os.environ.get("SAAS_ADMIN_TOKEN")
    previous_warning = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD")
    previous_critical = os.environ.get("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD")

    marker = "rid=ph279rbkqslareview"
    try:
        os.environ["SAAS_ADMIN_TOKEN"] = "phase279-token"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = "0.3"
        os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = "0.8"

        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase279-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-27;to=2026-02-27;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 27, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase279-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-02-28;to=2026-02-28;b=2;s=0;d=0",
                created_at=datetime(2026, 2, 28, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase279-client",
                outcome="replay",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 0, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase279-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-01;to=2026-03-01;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 1, 10, 5, 0),
            )
        )
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip="phase279-client",
                outcome="success",
                deleted_keys=2,
                reason=f"op=backfill;{marker};from=2026-03-02;to=2026-03-02;b=2;s=0;d=0",
                created_at=datetime(2026, 3, 2, 10, 0, 0),
            )
        )
        session.commit()

        response = client.get(
            "/saas/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/receipt/review"
            "?from=2026-03-01&to=2026-03-02&operation=backfill",
            headers={"X-Admin-Token": "phase279-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["review_state"] == "priority_review"
        assert payload["review_required"] is True
        assert payload["receipt_status"] == "sent_priority"
        assert payload["dispatch_mode"] == "on-call"
        assert payload["notify_channel"] == "ops-alert"
        assert payload["decision"] == "escalate_follow_up"
        assert payload["action"] == "page_and_follow_up"
        assert payload["watch_state"] == "attention"
        assert payload["should_page"] is True
        assert payload["escalation_mode"] == "expedited"
        assert payload["follow_up_in_minutes"] == 15
        assert payload["sla_status"] == "on_track"
        assert payload["breach_risk"] == "medium"
        assert payload["ticket_type"] == "incident"
        assert payload["ticket_state"] == "open"
        assert payload["ticket_severity"] == "sev2"
        assert payload["queue_name"] == "ops-action-required"
        assert payload["queue_priority"] == "p2"
        assert payload["ack_required"] is True
        assert payload["ack_deadline_minutes"] == 30
        assert payload["status"] == "warning"
        assert payload["trend"] == "worsening"
        assert payload["priority"] == "medium"
    finally:
        client.close()
        session.query(SaaSAdminAuditEventModel).filter(
            SaaSAdminAuditEventModel.event_type == "audit_metrics_operation",
            SaaSAdminAuditEventModel.reason.like("%ph279rbkqslareview%"),
        ).delete(synchronize_session=False)
        session.commit()
        session.close()

        if previous_token is None:
            os.environ.pop("SAAS_ADMIN_TOKEN", None)
        else:
            os.environ["SAAS_ADMIN_TOKEN"] = previous_token

        if previous_warning is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD"] = previous_warning

        if previous_critical is None:
            os.environ.pop("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", None)
        else:
            os.environ["SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD"] = previous_critical
