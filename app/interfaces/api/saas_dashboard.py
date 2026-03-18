from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status

from app.application.use_cases.get_saas_dashboard import GetSaaSDashboardUseCase
from app.application.use_cases.get_journey_funnel import GetJourneyFunnelUseCase
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.models import SaaSAdminAuditEventModel, UserModel
from app.interfaces.dependencies.auth import get_current_user
from app.interfaces.dependencies import (
    get_saas_dashboard_use_case, 
    get_journey_funnel_use_case
)

router = APIRouter(prefix="/saas", tags=["saas"])
logger = logging.getLogger(__name__)


def _resolve_effective_hotel_id(user: UserModel, x_hotel_id: str | None) -> str | None:
    """
    Resolve o hotel efetivo a ser usado nos endpoints SaaS.

    Regra:
    - Se o usuário tiver `hotel_id` atrelado, sempre usa esse (funcionário/manager de um hotel).
    - Se NÃO tiver `hotel_id` mas for papel administrativo (admin/superadmin/owner),
      pode usar o hotel vindo no header `X-Hotel-Id`.
    """
    if user.hotel_id:
        return user.hotel_id

    admin_roles = {"admin", "superadmin", "owner", "system_admin"}
    if getattr(user, "role", None) in admin_roles and x_hotel_id:
        return x_hotel_id

    return None


def _audit_cache_invalidate(
    client_ip: str,
    outcome: str,
    deleted_keys: int | None = None,
    retry_after: int | None = None,
    reason: str | None = None,
) -> None:
    logger.info(
        "saas_cache_invalidate_audit",
        extra={
            "client_ip": client_ip,
            "outcome": outcome,
            "deleted_keys": deleted_keys,
            "retry_after": retry_after,
            "reason": reason,
        },
    )

    session = SessionLocal()
    try:
        session.add(
            SaaSAdminAuditEventModel(
                event_type="cache_invalidate",
                client_ip=client_ip,
                outcome=outcome,
                deleted_keys=deleted_keys,
                retry_after=retry_after,
                reason=reason,
            )
        )
        session.commit()
    except Exception as exc:
        logger.warning(f"⚠️ Failed to persist cache invalidation audit event: {exc}")
        session.rollback()
    finally:
        session.close()


def _build_snapshot_operation_reason(
    operation: str,
    request_id: str | None,
    from_date: date,
    to_date: date,
    batch_size: int,
    summary_only: bool,
    dry_run: bool,
) -> str:
    request_fragment = (request_id or "-")[:24]
    reason = (
        f"op={operation};rid={request_fragment};"
        f"from={from_date.isoformat()};to={to_date.isoformat()};"
        f"b={batch_size};s={1 if summary_only else 0};d={1 if dry_run else 0}"
    )
    return reason[:120]


def _audit_snapshot_operation(
    client_ip: str,
    operation: str,
    outcome: str,
    created: int,
    reason: str,
) -> None:
    logger.info(
        "saas_snapshot_operation_audit",
        extra={
            "client_ip": client_ip,
            "operation": operation,
            "outcome": outcome,
            "created": created,
            "reason": reason,
        },
    )

    session = SessionLocal()
    try:
        session.add(
            SaaSAdminAuditEventModel(
                event_type="audit_metrics_operation",
                client_ip=client_ip,
                outcome=outcome,
                deleted_keys=created,
                reason=reason,
            )
        )
        session.commit()
    except Exception as exc:
        logger.warning(f"⚠️ Failed to persist snapshot operation audit event: {exc}")
        session.rollback()
    finally:
        session.close()


def _assert_admin_token_or_raise(x_admin_token: str | None) -> None:
    configured_token = os.getenv("SAAS_ADMIN_TOKEN")
    if not configured_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SAAS_ADMIN_TOKEN is not configured",
        )

    if not x_admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Admin-Token header",
        )

    if x_admin_token != configured_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
        )


def _resolve_alert(
    current_ratio: float,
    warning_threshold: float,
    critical_threshold: float,
) -> dict:
    if critical_threshold < warning_threshold:
        critical_threshold = warning_threshold

    if current_ratio > critical_threshold:
        status_label = "critical"
    elif current_ratio > warning_threshold:
        status_label = "warning"
    else:
        status_label = "healthy"

    return {
        "metric": "rate_limited_ratio",
        "current": round(current_ratio, 4),
        "warning_threshold": warning_threshold,
        "critical_threshold": critical_threshold,
        "status": status_label,
    }


def _resolve_operations_replay_alert(
    replay_ratio: float,
    warning_threshold: float,
    critical_threshold: float,
) -> dict:
    if critical_threshold < warning_threshold:
        critical_threshold = warning_threshold

    if replay_ratio > critical_threshold:
        status_label = "critical"
    elif replay_ratio > warning_threshold:
        status_label = "warning"
    else:
        status_label = "healthy"

    return {
        "metric": "operations_replay_ratio",
        "current": round(replay_ratio, 4),
        "warning_threshold": warning_threshold,
        "critical_threshold": critical_threshold,
        "status": status_label,
    }


def _build_operations_recommendations(alert_status: str, replay_count: int, total_operations: int) -> list[str]:
    if alert_status == "critical":
        return [
            "Ativar investigação imediata dos replays por request_id e operação.",
            "Validar estabilidade dos workers/jobs antes de novas execuções em massa.",
            "Executar operações críticas com dry_run e janelas menores até estabilizar.",
        ]
    if alert_status == "warning":
        return [
            "Revisar operações com replay recente e confirmar se são reenvios esperados.",
            "Ajustar batch_size e janela para reduzir risco de repetição operacional.",
        ]
    if total_operations == 0:
        return [
            "Sem operações no período; manter monitoramento regular.",
        ]
    if replay_count == 0:
        return [
            "Operação saudável sem replays; manter parâmetros atuais.",
        ]
    return [
        "Replays controlados; manter monitoramento e revisão periódica.",
    ]


def _build_operations_status_history_items_and_summary(
    raw_items: list[dict],
    warning_threshold: float,
    critical_threshold: float,
) -> tuple[list[dict], dict]:
    items: list[dict] = []
    by_status = {"healthy": 0, "warning": 0, "critical": 0}
    action_required_days = 0

    for item in raw_items:
        replay_ratio = float(item.get("replay_ratio", 0.0) or 0.0)
        alert = _resolve_operations_replay_alert(
            replay_ratio=replay_ratio,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
        )
        status_label = str(alert.get("status", "healthy"))
        by_status[status_label] = by_status.get(status_label, 0) + 1
        if status_label in {"warning", "critical"}:
            action_required_days += 1

        items.append(
            {
                **item,
                "status": status_label,
                "action_required": status_label in {"warning", "critical"},
                "alert": alert,
            }
        )

    summary = {
        "days": len(items),
        "by_status": by_status,
        "action_required_days": action_required_days,
    }
    return items, summary


def _build_operations_status_history_compare_payload(
    from_date: date,
    to_date: date,
    operation: str | None,
    use_case: GetSaaSDashboardUseCase,
) -> dict:
    _assert_range_limit_or_raise(from_date, to_date)
    window_days = (to_date - from_date).days + 1
    previous_to = from_date - timedelta(days=1)
    previous_from = previous_to - timedelta(days=window_days - 1)

    warning_threshold = float(os.getenv("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", "0.15"))
    critical_threshold = float(os.getenv("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", "0.35"))

    current_raw_items = use_case.get_admin_audit_metric_operations_metrics_history(
        start_date=from_date,
        end_date=to_date,
        operation=operation,
    )
    previous_raw_items = use_case.get_admin_audit_metric_operations_metrics_history(
        start_date=previous_from,
        end_date=previous_to,
        operation=operation,
    )

    _, current_summary = _build_operations_status_history_items_and_summary(
        raw_items=current_raw_items,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
    )
    _, previous_summary = _build_operations_status_history_items_and_summary(
        raw_items=previous_raw_items,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
    )

    delta = {
        "action_required_days": int(current_summary.get("action_required_days", 0)) - int(previous_summary.get("action_required_days", 0)),
        "warning_days": int(current_summary.get("by_status", {}).get("warning", 0)) - int(previous_summary.get("by_status", {}).get("warning", 0)),
        "critical_days": int(current_summary.get("by_status", {}).get("critical", 0)) - int(previous_summary.get("by_status", {}).get("critical", 0)),
    }

    return {
        "current_period": {
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "operation": operation,
            "summary": current_summary,
        },
        "previous_period": {
            "from": previous_from.isoformat(),
            "to": previous_to.isoformat(),
            "operation": operation,
            "summary": previous_summary,
        },
        "delta": delta,
    }


def _resolve_operations_status_trend(
    delta_action_required_days: int,
    delta_warning_days: int,
    delta_critical_days: int,
) -> str:
    if delta_critical_days > 0 or delta_action_required_days > 0 or delta_warning_days > 0:
        return "worsening"
    if delta_critical_days < 0 or delta_action_required_days < 0 or delta_warning_days < 0:
        return "improving"
    return "stable"


def _build_operations_trend_recommendations(
    trend: str,
    current_critical_days: int,
    current_action_required_days: int,
) -> list[str]:
    if trend == "worsening":
        return [
            "Aumentar frequência de monitoramento até estabilizar a tendência.",
            "Revisar operações com replay e reduzir janela/batch quando necessário.",
            "Priorizar investigação de dias críticos no período atual.",
        ]
    if trend == "improving":
        return [
            "Tendência de risco em queda; manter parâmetros atuais e monitoramento diário.",
            "Registrar ajustes que contribuíram para a melhora para padronização operacional.",
        ]
    if current_critical_days > 0 or current_action_required_days > 0:
        return [
            "Tendência estável, porém ainda há dias com risco; manter plano de mitigação ativo.",
        ]
    return [
        "Tendência estável e saudável; manter cadência operacional padrão.",
    ]


def _resolve_operations_trend_alert(
    delta_action_required_days: int,
    delta_warning_days: int,
    delta_critical_days: int,
    current_action_required_days: int,
    current_critical_days: int,
) -> dict:
    if delta_critical_days > 0 or current_critical_days > 0:
        status_label = "critical"
    elif delta_action_required_days > 0 or delta_warning_days > 0 or current_action_required_days > 0:
        status_label = "warning"
    else:
        status_label = "healthy"

    return {
        "metric": "operations_status_trend",
        "status": status_label,
        "current_action_required_days": current_action_required_days,
        "current_critical_days": current_critical_days,
        "delta_action_required_days": delta_action_required_days,
        "delta_warning_days": delta_warning_days,
        "delta_critical_days": delta_critical_days,
    }


def _resolve_operations_priority(status_label: str) -> str:
    if status_label == "critical":
        return "high"
    if status_label == "warning":
        return "medium"
    return "low"


def _build_operations_trend_headline(status_label: str, trend: str) -> str:
    if status_label == "critical":
        return "Risco operacional crítico na tendência; ação imediata recomendada."
    if status_label == "warning" and trend == "worsening":
        return "Tendência em piora com risco moderado; aumentar monitoramento."
    if status_label == "warning":
        return "Risco moderado na tendência; manter plano de mitigação ativo."
    if trend == "improving":
        return "Tendência operacional em melhora e sem risco ativo."
    return "Tendência operacional estável e saudável."


def _resolve_operations_brief_decision(status_label: str, trend: str) -> dict:
    if status_label == "critical":
        return {
            "decision": "escalate",
            "reason": "Risco crítico ativo no período atual.",
        }
    if status_label == "warning" and trend == "worsening":
        return {
            "decision": "investigate",
            "reason": "Risco moderado em piora requer investigação imediata.",
        }
    if status_label == "warning":
        return {
            "decision": "investigate",
            "reason": "Risco moderado presente; manter mitigação e revisão operacional.",
        }
    return {
        "decision": "monitor",
        "reason": "Cenário saudável; seguir monitoramento padrão.",
    }


def _build_operations_brief_notice(status_label: str, trend: str, decision: str) -> dict:
    if decision == "escalate":
        return {
            "title": "Escalonar incidente operacional",
            "message": "Risco crítico identificado; acionar resposta imediata e revisão do backlog de operações.",
        }
    if decision == "investigate" and trend == "worsening":
        return {
            "title": "Investigar piora de tendência",
            "message": "Risco moderado em alta; revisar replays recentes e ajustar batch/janela antes do próximo ciclo.",
        }
    if decision == "investigate":
        return {
            "title": "Investigar risco moderado",
            "message": "Risco ativo detectado; manter mitigação e validar operações com anomalia.",
        }
    if status_label == "healthy" and trend == "improving":
        return {
            "title": "Monitorar tendência em melhora",
            "message": "Sem risco ativo; manter monitoramento e registrar práticas que reduziram o risco.",
        }
    return {
        "title": "Monitoramento operacional padrão",
        "message": "Cenário estável e saudável; seguir com a cadência normal de acompanhamento.",
    }


def _resolve_operations_notice_dispatch_channel(priority: str, action_required: bool) -> str:
    if priority == "high":
        return "incident"
    if action_required:
        return "ops-alert"
    return "ops-monitor"


def _resolve_operations_notice_dispatch_targets(channel: str) -> list[str]:
    default_targets_by_channel = {
        "incident": "oncall-incident",
        "ops-alert": "oncall-ops",
        "ops-monitor": "ops-daily",
    }
    env_key = f"SAAS_AUDIT_DISPATCH_TARGETS_{channel.replace('-', '_').upper()}"
    configured = os.getenv(env_key, "")
    if configured.strip():
        targets = [item.strip() for item in configured.split(",") if item.strip()]
        if targets:
            return targets
    return [default_targets_by_channel.get(channel, "ops-daily")]


def _assert_range_limit_or_raise(from_date: date, to_date: date) -> None:
    if to_date < from_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="'to' must be greater than or equal to 'from'",
        )

    max_range_days = int(os.getenv("SAAS_AUDIT_SNAPSHOT_MAX_RANGE_DAYS", "90"))
    max_range_days = max(1, max_range_days)
    total_days = (to_date - from_date).days + 1
    if total_days > max_range_days:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Date range too large: {total_days} days (max {max_range_days})",
        )


def _resolve_batch_size(batch_size: int | None) -> int:
    default_batch_size = int(os.getenv("SAAS_AUDIT_SNAPSHOT_BATCH_SIZE", "30"))
    default_batch_size = max(1, default_batch_size)
    resolved = int(batch_size or default_batch_size)
    return max(1, min(200, resolved))


def _operation_idempotency_ttl_seconds() -> int:
    ttl = int(os.getenv("SAAS_AUDIT_OPERATION_IDEMPOTENCY_TTL_SECONDS", "86400"))
    return max(60, ttl)


def _build_operation_idempotency_key(
    operation: str,
    request_id: str,
    payload: dict,
) -> str:
    normalized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"saas:audit_ops:idempotency:{operation}:{request_id}:{digest}"


def _try_get_cached_idempotent_response(use_case: GetSaaSDashboardUseCase, cache_key: str) -> dict | None:
    cache_repository = getattr(use_case, "cache_repository", None)
    if cache_repository is None:
        return None
    try:
        return cache_repository.get(cache_key)
    except Exception:
        return None


def _try_set_cached_idempotent_response(use_case: GetSaaSDashboardUseCase, cache_key: str, payload: dict) -> None:
    cache_repository = getattr(use_case, "cache_repository", None)
    if cache_repository is None:
        return
    try:
        cache_repository.set(
            cache_key,
            payload,
            ttl_seconds=_operation_idempotency_ttl_seconds(),
        )
    except Exception:
        return


@router.get("/audit-events")
def get_audit_events(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    outcome: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)
    return use_case.get_admin_audit_events(
        start_date=from_date,
        end_date=to_date,
        outcome=outcome,
        page=page,
        page_size=page_size,
    )


@router.get("/audit-events/export")
def export_audit_events_csv(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    outcome: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    items = use_case.get_admin_audit_events_for_export(
        start_date=from_date,
        end_date=to_date,
        outcome=outcome,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "event_type",
        "client_ip",
        "outcome",
        "deleted_keys",
        "retry_after",
        "reason",
        "created_at",
    ])

    for item in items:
        writer.writerow([
            item.get("id"),
            item.get("event_type"),
            item.get("client_ip"),
            item.get("outcome"),
            item.get("deleted_keys"),
            item.get("retry_after"),
            item.get("reason"),
            item.get("created_at"),
        ])

    filename = "saas_audit_events.csv"
    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/audit-events/metrics")
def get_audit_events_metrics(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)
    metrics = use_case.get_admin_audit_metrics(
        start_date=from_date,
        end_date=to_date,
    )

    warning_threshold = float(os.getenv("SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD", "0.2"))
    critical_threshold = float(os.getenv("SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD", "0.5"))
    current_ratio = float(metrics.get("rate_limited", {}).get("ratio", 0.0) or 0.0)
    metrics["alert"] = _resolve_alert(
        current_ratio=current_ratio,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
    )
    return metrics


@router.post("/audit-events/metrics/snapshot")
def create_audit_metrics_snapshot(
    snapshot_date: date | None = Query(default=None, alias="date"),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    target_date = snapshot_date or date.today()
    start_date = from_date or target_date
    end_date = to_date or target_date

    metrics = use_case.get_admin_audit_metrics(start_date=start_date, end_date=end_date)
    warning_threshold = float(os.getenv("SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD", "0.2"))
    critical_threshold = float(os.getenv("SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD", "0.5"))
    current_ratio = float(metrics.get("rate_limited", {}).get("ratio", 0.0) or 0.0)
    alert = _resolve_alert(
        current_ratio=current_ratio,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
    )

    snapshot = use_case.create_admin_audit_metrics_snapshot(
        snapshot_date=target_date,
        start_date=start_date,
        end_date=end_date,
        warning_threshold=float(alert["warning_threshold"]),
        critical_threshold=float(alert["critical_threshold"]),
        alert_status=str(alert["status"]),
    )

    return {
        "snapshot": snapshot,
        "alert": alert,
        "period": {
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
        },
    }


@router.get("/audit-events/metrics/history")
def get_audit_metrics_history(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)
    return use_case.get_admin_audit_metrics_snapshots(
        start_date=from_date,
        end_date=to_date,
    )


@router.get("/audit-events/metrics/operations")
def get_audit_metric_operations(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    outcome: str | None = Query(default=None),
    operation: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)
    return use_case.get_admin_audit_metric_operations(
        start_date=from_date,
        end_date=to_date,
        outcome=outcome,
        operation=operation,
        request_id=request_id,
        page=page,
        page_size=page_size,
    )


@router.get("/audit-events/metrics/operations/export")
def export_audit_metric_operations_csv(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    outcome: str | None = Query(default=None),
    operation: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    items = use_case.get_admin_audit_metric_operations_for_export(
        start_date=from_date,
        end_date=to_date,
        outcome=outcome,
        operation=operation,
        request_id=request_id,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "event_type",
        "client_ip",
        "outcome",
        "processed_count",
        "operation",
        "request_id",
        "reason",
        "created_at",
    ])

    for item in items:
        writer.writerow([
            item.get("id"),
            item.get("event_type"),
            item.get("client_ip"),
            item.get("outcome"),
            item.get("processed_count"),
            item.get("operation"),
            item.get("request_id"),
            item.get("reason"),
            item.get("created_at"),
        ])

    filename = "saas_audit_metric_operations.csv"
    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/audit-events/metrics/operations/metrics")
def get_audit_metric_operations_metrics(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    operation: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)
    payload = use_case.get_admin_audit_metric_operations_metrics(
        start_date=from_date,
        end_date=to_date,
        operation=operation,
        request_id=request_id,
    )

    warning_threshold = float(os.getenv("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", "0.15"))
    critical_threshold = float(os.getenv("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", "0.35"))
    replay_ratio = float(payload.get("replay_ratio", 0.0) or 0.0)

    payload["alert"] = _resolve_operations_replay_alert(
        replay_ratio=replay_ratio,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
    )
    return payload


@router.get("/audit-events/metrics/operations/status")
def get_audit_metric_operations_status(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    operation: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    target_day = date.today()
    start_date = from_date or target_day
    end_date = to_date or target_day
    _assert_range_limit_or_raise(start_date, end_date)

    metrics = use_case.get_admin_audit_metric_operations_metrics(
        start_date=start_date,
        end_date=end_date,
        operation=operation,
        request_id=request_id,
    )

    warning_threshold = float(os.getenv("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", "0.15"))
    critical_threshold = float(os.getenv("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", "0.35"))
    replay_ratio = float(metrics.get("replay_ratio", 0.0) or 0.0)
    alert = _resolve_operations_replay_alert(
        replay_ratio=replay_ratio,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
    )
    alert_status = str(alert.get("status", "healthy"))
    total_operations = int(metrics.get("total_operations", 0) or 0)
    replay_count = int(metrics.get("replay_count", 0) or 0)

    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    return {
        "status": alert_status,
        "action_required": alert_status in {"warning", "critical"},
        "alert": alert,
        "metrics": {
            "total_operations": total_operations,
            "replay_count": replay_count,
            "replay_ratio": round(replay_ratio, 4),
            "dry_run_count": int(metrics.get("dry_run_count", 0) or 0),
            "success_count": int(metrics.get("success_count", 0) or 0),
        },
        "recommendations": _build_operations_recommendations(
            alert_status=alert_status,
            replay_count=replay_count,
            total_operations=total_operations,
        ),
        "period": {
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "operation": operation,
            "request_id": request_id,
        },
        "next_check_in_minutes": check_interval_minutes,
    }


@router.get("/audit-events/metrics/operations/status/history")
def get_audit_metric_operations_status_history(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    today = date.today()
    start_date = from_date or (today - timedelta(days=6))
    end_date = to_date or today
    _assert_range_limit_or_raise(start_date, end_date)

    warning_threshold = float(os.getenv("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", "0.15"))
    critical_threshold = float(os.getenv("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", "0.35"))

    raw_items = use_case.get_admin_audit_metric_operations_metrics_history(
        start_date=start_date,
        end_date=end_date,
        operation=operation,
    )

    items, summary = _build_operations_status_history_items_and_summary(
        raw_items=raw_items,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
    )

    return {
        "period": {
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "operation": operation,
        },
        "items": items,
        "summary": {
            "days": summary["days"],
            "by_status": summary["by_status"],
            "action_required_days": summary["action_required_days"],
        },
    }


@router.get("/audit-events/metrics/operations/status/history/compare")
def get_audit_metric_operations_status_history_compare(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    return _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )


@router.get("/audit-events/metrics/operations/status/history/compare/export")
def export_audit_metric_operations_status_history_compare_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    previous_summary = payload.get("previous_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "current_from",
        "current_to",
        "previous_from",
        "previous_to",
        "operation",
        "current_days",
        "current_healthy_days",
        "current_warning_days",
        "current_critical_days",
        "current_action_required_days",
        "previous_days",
        "previous_healthy_days",
        "previous_warning_days",
        "previous_critical_days",
        "previous_action_required_days",
        "delta_action_required_days",
        "delta_warning_days",
        "delta_critical_days",
    ])
    writer.writerow([
        payload.get("current_period", {}).get("from"),
        payload.get("current_period", {}).get("to"),
        payload.get("previous_period", {}).get("from"),
        payload.get("previous_period", {}).get("to"),
        operation,
        int(current_summary.get("days", 0) or 0),
        int(current_summary.get("by_status", {}).get("healthy", 0) or 0),
        int(current_summary.get("by_status", {}).get("warning", 0) or 0),
        int(current_summary.get("by_status", {}).get("critical", 0) or 0),
        int(current_summary.get("action_required_days", 0) or 0),
        int(previous_summary.get("days", 0) or 0),
        int(previous_summary.get("by_status", {}).get("healthy", 0) or 0),
        int(previous_summary.get("by_status", {}).get("warning", 0) or 0),
        int(previous_summary.get("by_status", {}).get("critical", 0) or 0),
        int(previous_summary.get("action_required_days", 0) or 0),
        int(delta.get("action_required_days", 0) or 0),
        int(delta.get("warning_days", 0) or 0),
        int(delta.get("critical_days", 0) or 0),
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_history_compare.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend")
def get_audit_metric_operations_status_trend(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )

    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    return {
        **payload,
        "trend": trend,
        "action_required": trend == "worsening",
        "recommendations": _build_operations_trend_recommendations(
            trend=trend,
            current_critical_days=current_critical_days,
            current_action_required_days=current_action_required_days,
        ),
    }


@router.get("/audit-events/metrics/operations/status/trend/export")
def export_audit_metric_operations_status_trend_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )

    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)
    action_required = trend == "worsening"
    recommendations = _build_operations_trend_recommendations(
        trend=trend,
        current_critical_days=current_critical_days,
        current_action_required_days=current_action_required_days,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "current_from",
        "current_to",
        "previous_from",
        "previous_to",
        "operation",
        "trend",
        "action_required",
        "delta_action_required_days",
        "delta_warning_days",
        "delta_critical_days",
        "recommendations",
    ])
    writer.writerow([
        payload.get("current_period", {}).get("from"),
        payload.get("current_period", {}).get("to"),
        payload.get("previous_period", {}).get("from"),
        payload.get("previous_period", {}).get("to"),
        operation,
        trend,
        "true" if action_required else "false",
        delta_action_required_days,
        delta_warning_days,
        delta_critical_days,
        " | ".join(recommendations),
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/status")
def get_audit_metric_operations_status_trend_status(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )

    return {
        **payload,
        "trend": trend,
        "alert": alert,
        "status": str(alert.get("status", "healthy")),
        "action_required": str(alert.get("status", "healthy")) in {"warning", "critical"},
        "recommendations": _build_operations_trend_recommendations(
            trend=trend,
            current_critical_days=current_critical_days,
            current_action_required_days=current_action_required_days,
        ),
    }


@router.get("/audit-events/metrics/operations/status/trend/status/export")
def export_audit_metric_operations_status_trend_status_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    action_required = status_label in {"warning", "critical"}
    recommendations = _build_operations_trend_recommendations(
        trend=trend,
        current_critical_days=current_critical_days,
        current_action_required_days=current_action_required_days,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "current_from",
        "current_to",
        "previous_from",
        "previous_to",
        "operation",
        "status",
        "trend",
        "action_required",
        "current_action_required_days",
        "current_critical_days",
        "delta_action_required_days",
        "delta_warning_days",
        "delta_critical_days",
        "recommendations",
    ])
    writer.writerow([
        payload.get("current_period", {}).get("from"),
        payload.get("current_period", {}).get("to"),
        payload.get("previous_period", {}).get("from"),
        payload.get("previous_period", {}).get("to"),
        operation,
        status_label,
        trend,
        "true" if action_required else "false",
        current_action_required_days,
        current_critical_days,
        delta_action_required_days,
        delta_warning_days,
        delta_critical_days,
        " | ".join(recommendations),
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_status.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview")
def get_audit_metric_operations_status_trend_overview(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    action_required = status_label in {"warning", "critical"}
    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    return {
        "period": {
            "current": {
                "from": payload.get("current_period", {}).get("from"),
                "to": payload.get("current_period", {}).get("to"),
            },
            "previous": {
                "from": payload.get("previous_period", {}).get("from"),
                "to": payload.get("previous_period", {}).get("to"),
            },
            "operation": operation,
        },
        "status": status_label,
        "trend": trend,
        "priority": _resolve_operations_priority(status_label),
        "headline": _build_operations_trend_headline(status_label, trend),
        "action_required": action_required,
        "alert": alert,
        "snapshot": {
            "current_action_required_days": current_action_required_days,
            "current_critical_days": current_critical_days,
            "delta_action_required_days": delta_action_required_days,
            "delta_warning_days": delta_warning_days,
            "delta_critical_days": delta_critical_days,
        },
        "next_check_in_minutes": check_interval_minutes,
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/export")
def export_audit_metric_operations_status_trend_overview_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    priority = _resolve_operations_priority(status_label)
    headline = _build_operations_trend_headline(status_label, trend)
    action_required = status_label in {"warning", "critical"}
    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "current_from",
        "current_to",
        "previous_from",
        "previous_to",
        "operation",
        "status",
        "trend",
        "priority",
        "headline",
        "action_required",
        "current_action_required_days",
        "current_critical_days",
        "delta_action_required_days",
        "delta_warning_days",
        "delta_critical_days",
        "next_check_in_minutes",
    ])
    writer.writerow([
        payload.get("current_period", {}).get("from"),
        payload.get("current_period", {}).get("to"),
        payload.get("previous_period", {}).get("from"),
        payload.get("previous_period", {}).get("to"),
        operation,
        status_label,
        trend,
        priority,
        headline,
        "true" if action_required else "false",
        current_action_required_days,
        current_critical_days,
        delta_action_required_days,
        delta_warning_days,
        delta_critical_days,
        check_interval_minutes,
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief")
def get_audit_metric_operations_status_trend_overview_brief(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    return {
        "status": status_label,
        "trend": trend,
        "priority": _resolve_operations_priority(status_label),
        "headline": _build_operations_trend_headline(status_label, trend),
        "action_required": status_label in {"warning", "critical"},
        "operation": operation,
        "period": {
            "from": payload.get("current_period", {}).get("from"),
            "to": payload.get("current_period", {}).get("to"),
        },
        "snapshot": {
            "current_action_required_days": current_action_required_days,
            "current_critical_days": current_critical_days,
            "delta_action_required_days": delta_action_required_days,
            "delta_warning_days": delta_warning_days,
            "delta_critical_days": delta_critical_days,
        },
        "next_check_in_minutes": check_interval_minutes,
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/export")
def export_audit_metric_operations_status_trend_overview_brief_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    priority = _resolve_operations_priority(status_label)
    headline = _build_operations_trend_headline(status_label, trend)
    action_required = status_label in {"warning", "critical"}
    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "current_from",
        "current_to",
        "operation",
        "status",
        "trend",
        "priority",
        "headline",
        "action_required",
        "current_action_required_days",
        "current_critical_days",
        "delta_action_required_days",
        "delta_warning_days",
        "delta_critical_days",
        "next_check_in_minutes",
    ])
    writer.writerow([
        payload.get("current_period", {}).get("from"),
        payload.get("current_period", {}).get("to"),
        operation,
        status_label,
        trend,
        priority,
        headline,
        "true" if action_required else "false",
        current_action_required_days,
        current_critical_days,
        delta_action_required_days,
        delta_warning_days,
        delta_critical_days,
        check_interval_minutes,
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision")
def get_audit_metric_operations_status_trend_overview_brief_decision(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    decision_payload = _resolve_operations_brief_decision(status_label, trend)
    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    return {
        "status": status_label,
        "trend": trend,
        "priority": _resolve_operations_priority(status_label),
        "decision": decision_payload.get("decision"),
        "reason": decision_payload.get("reason"),
        "action_required": status_label in {"warning", "critical"},
        "operation": operation,
        "period": {
            "from": payload.get("current_period", {}).get("from"),
            "to": payload.get("current_period", {}).get("to"),
        },
        "snapshot": {
            "current_action_required_days": current_action_required_days,
            "current_critical_days": current_critical_days,
            "delta_action_required_days": delta_action_required_days,
            "delta_warning_days": delta_warning_days,
            "delta_critical_days": delta_critical_days,
        },
        "next_check_in_minutes": check_interval_minutes,
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/export")
def export_audit_metric_operations_status_trend_overview_brief_decision_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    priority = _resolve_operations_priority(status_label)
    decision_payload = _resolve_operations_brief_decision(status_label, trend)
    action_required = status_label in {"warning", "critical"}
    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "current_from",
        "current_to",
        "operation",
        "status",
        "trend",
        "priority",
        "decision",
        "reason",
        "action_required",
        "current_action_required_days",
        "current_critical_days",
        "delta_action_required_days",
        "delta_warning_days",
        "delta_critical_days",
        "next_check_in_minutes",
    ])
    writer.writerow([
        payload.get("current_period", {}).get("from"),
        payload.get("current_period", {}).get("to"),
        operation,
        status_label,
        trend,
        priority,
        decision_payload.get("decision"),
        decision_payload.get("reason"),
        "true" if action_required else "false",
        current_action_required_days,
        current_critical_days,
        delta_action_required_days,
        delta_warning_days,
        delta_critical_days,
        check_interval_minutes,
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief_decision.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice")
def get_audit_metric_operations_status_trend_overview_brief_decision_notice(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    priority = _resolve_operations_priority(status_label)
    decision_payload = _resolve_operations_brief_decision(status_label, trend)
    decision = str(decision_payload.get("decision", "monitor"))
    notice = _build_operations_brief_notice(status_label, trend, decision)
    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    return {
        "status": status_label,
        "trend": trend,
        "priority": priority,
        "decision": decision,
        "title": notice.get("title"),
        "message": notice.get("message"),
        "action_required": status_label in {"warning", "critical"},
        "operation": operation,
        "period": {
            "from": payload.get("current_period", {}).get("from"),
            "to": payload.get("current_period", {}).get("to"),
        },
        "next_check_in_minutes": check_interval_minutes,
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/export")
def export_audit_metric_operations_status_trend_overview_brief_decision_notice_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    priority = _resolve_operations_priority(status_label)
    decision_payload = _resolve_operations_brief_decision(status_label, trend)
    decision = str(decision_payload.get("decision", "monitor"))
    notice = _build_operations_brief_notice(status_label, trend, decision)
    action_required = status_label in {"warning", "critical"}
    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "current_from",
        "current_to",
        "operation",
        "status",
        "trend",
        "priority",
        "decision",
        "title",
        "message",
        "action_required",
        "next_check_in_minutes",
    ])
    writer.writerow([
        payload.get("current_period", {}).get("from"),
        payload.get("current_period", {}).get("to"),
        operation,
        status_label,
        trend,
        priority,
        decision,
        notice.get("title"),
        notice.get("message"),
        "true" if action_required else "false",
        check_interval_minutes,
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief_decision_notice.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch")
def get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    priority = _resolve_operations_priority(status_label)
    decision_payload = _resolve_operations_brief_decision(status_label, trend)
    decision = str(decision_payload.get("decision", "monitor"))
    notice = _build_operations_brief_notice(status_label, trend, decision)
    action_required = status_label in {"warning", "critical"}
    channel = _resolve_operations_notice_dispatch_channel(priority, action_required)
    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    period_from = payload.get("current_period", {}).get("from")
    period_to = payload.get("current_period", {}).get("to")
    dedupe_key = f"ops-trend-notice:{operation or 'all'}:{period_from}:{period_to}:{status_label}:{decision}"

    return {
        "channel": channel,
        "dedupe_key": dedupe_key,
        "title": notice.get("title"),
        "message": notice.get("message"),
        "status": status_label,
        "trend": trend,
        "priority": priority,
        "decision": decision,
        "action_required": action_required,
        "operation": operation,
        "period": {
            "from": period_from,
            "to": period_to,
        },
        "next_check_in_minutes": check_interval_minutes,
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/export")
def export_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    priority = _resolve_operations_priority(status_label)
    decision_payload = _resolve_operations_brief_decision(status_label, trend)
    decision = str(decision_payload.get("decision", "monitor"))
    notice = _build_operations_brief_notice(status_label, trend, decision)
    action_required = status_label in {"warning", "critical"}
    channel = _resolve_operations_notice_dispatch_channel(priority, action_required)
    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    period_from = payload.get("current_period", {}).get("from")
    period_to = payload.get("current_period", {}).get("to")
    dedupe_key = f"ops-trend-notice:{operation or 'all'}:{period_from}:{period_to}:{status_label}:{decision}"

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "channel",
        "dedupe_key",
        "title",
        "message",
        "status",
        "trend",
        "priority",
        "decision",
        "action_required",
        "operation",
        "period_from",
        "period_to",
        "next_check_in_minutes",
    ])
    writer.writerow([
        channel,
        dedupe_key,
        notice.get("title"),
        notice.get("message"),
        status_label,
        trend,
        priority,
        decision,
        "true" if action_required else "false",
        operation,
        period_from,
        period_to,
        check_interval_minutes,
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes")
def get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    priority = _resolve_operations_priority(status_label)
    action_required = status_label in {"warning", "critical"}
    channel = _resolve_operations_notice_dispatch_channel(priority, action_required)
    fallback_channel = "ops-monitor"
    targets = _resolve_operations_notice_dispatch_targets(channel)
    fallback_targets = _resolve_operations_notice_dispatch_targets(fallback_channel)
    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    period_from = payload.get("current_period", {}).get("from")
    period_to = payload.get("current_period", {}).get("to")
    dedupe_key = f"ops-trend-notice:{operation or 'all'}:{period_from}:{period_to}:{status_label}:{channel}"

    return {
        "channel": channel,
        "targets": targets,
        "fallback_channel": fallback_channel,
        "fallback_targets": fallback_targets,
        "dedupe_key": dedupe_key,
        "status": status_label,
        "trend": trend,
        "priority": priority,
        "action_required": action_required,
        "operation": operation,
        "period": {
            "from": period_from,
            "to": period_to,
        },
        "next_check_in_minutes": check_interval_minutes,
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/export")
def export_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    priority = _resolve_operations_priority(status_label)
    action_required = status_label in {"warning", "critical"}
    channel = _resolve_operations_notice_dispatch_channel(priority, action_required)
    fallback_channel = "ops-monitor"
    targets = _resolve_operations_notice_dispatch_targets(channel)
    fallback_targets = _resolve_operations_notice_dispatch_targets(fallback_channel)
    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    period_from = payload.get("current_period", {}).get("from")
    period_to = payload.get("current_period", {}).get("to")
    dedupe_key = f"ops-trend-notice:{operation or 'all'}:{period_from}:{period_to}:{status_label}:{channel}"

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "channel",
        "targets",
        "fallback_channel",
        "fallback_targets",
        "dedupe_key",
        "status",
        "trend",
        "priority",
        "action_required",
        "operation",
        "period_from",
        "period_to",
        "next_check_in_minutes",
    ])
    writer.writerow([
        channel,
        " | ".join(targets),
        fallback_channel,
        " | ".join(fallback_targets),
        dedupe_key,
        status_label,
        trend,
        priority,
        "true" if action_required else "false",
        operation,
        period_from,
        period_to,
        check_interval_minutes,
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief")
def get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    priority = _resolve_operations_priority(status_label)
    action_required = status_label in {"warning", "critical"}
    channel = _resolve_operations_notice_dispatch_channel(priority, action_required)
    fallback_channel = "ops-monitor"
    targets = _resolve_operations_notice_dispatch_targets(channel)
    fallback_targets = _resolve_operations_notice_dispatch_targets(fallback_channel)
    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    period_from = payload.get("current_period", {}).get("from")
    period_to = payload.get("current_period", {}).get("to")

    return {
        "channel": channel,
        "primary_target": targets[0] if targets else None,
        "fallback_target": fallback_targets[0] if fallback_targets else None,
        "targets_count": len(targets),
        "fallback_targets_count": len(fallback_targets),
        "status": status_label,
        "trend": trend,
        "priority": priority,
        "action_required": action_required,
        "operation": operation,
        "period": {
            "from": period_from,
            "to": period_to,
        },
        "next_check_in_minutes": check_interval_minutes,
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/export")
def export_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    priority = _resolve_operations_priority(status_label)
    action_required = status_label in {"warning", "critical"}
    channel = _resolve_operations_notice_dispatch_channel(priority, action_required)
    fallback_channel = "ops-monitor"
    targets = _resolve_operations_notice_dispatch_targets(channel)
    fallback_targets = _resolve_operations_notice_dispatch_targets(fallback_channel)
    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    period_from = payload.get("current_period", {}).get("from")
    period_to = payload.get("current_period", {}).get("to")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "channel",
        "primary_target",
        "fallback_target",
        "targets_count",
        "fallback_targets_count",
        "status",
        "trend",
        "priority",
        "action_required",
        "operation",
        "period_from",
        "period_to",
        "next_check_in_minutes",
    ])
    writer.writerow([
        channel,
        targets[0] if targets else None,
        fallback_targets[0] if fallback_targets else None,
        len(targets),
        len(fallback_targets),
        status_label,
        trend,
        priority,
        "true" if action_required else "false",
        operation,
        period_from,
        period_to,
        check_interval_minutes,
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision")
def get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    priority = _resolve_operations_priority(status_label)
    action_required = status_label in {"warning", "critical"}
    channel = _resolve_operations_notice_dispatch_channel(priority, action_required)
    targets = _resolve_operations_notice_dispatch_targets(channel)
    fallback_targets = _resolve_operations_notice_dispatch_targets("ops-monitor")
    primary_target = targets[0] if targets else None
    fallback_target = fallback_targets[0] if fallback_targets else None

    if priority == "high":
        route_decision = "escalate_immediately"
    elif action_required:
        route_decision = "dispatch_primary"
    else:
        route_decision = "monitor_only"

    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    period_from = payload.get("current_period", {}).get("from")
    period_to = payload.get("current_period", {}).get("to")

    return {
        "route_decision": route_decision,
        "channel": channel,
        "primary_target": primary_target,
        "fallback_target": fallback_target,
        "status": status_label,
        "trend": trend,
        "priority": priority,
        "action_required": action_required,
        "operation": operation,
        "period": {
            "from": period_from,
            "to": period_to,
        },
        "next_check_in_minutes": check_interval_minutes,
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/export")
def export_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    priority = _resolve_operations_priority(status_label)
    action_required = status_label in {"warning", "critical"}
    channel = _resolve_operations_notice_dispatch_channel(priority, action_required)
    targets = _resolve_operations_notice_dispatch_targets(channel)
    fallback_targets = _resolve_operations_notice_dispatch_targets("ops-monitor")
    primary_target = targets[0] if targets else None
    fallback_target = fallback_targets[0] if fallback_targets else None

    if priority == "high":
        route_decision = "escalate_immediately"
    elif action_required:
        route_decision = "dispatch_primary"
    else:
        route_decision = "monitor_only"

    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    period_from = payload.get("current_period", {}).get("from")
    period_to = payload.get("current_period", {}).get("to")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "route_decision",
        "channel",
        "primary_target",
        "fallback_target",
        "status",
        "trend",
        "priority",
        "action_required",
        "operation",
        "period_from",
        "period_to",
        "next_check_in_minutes",
    ])
    writer.writerow([
        route_decision,
        channel,
        primary_target,
        fallback_target,
        status_label,
        trend,
        priority,
        "true" if action_required else "false",
        operation,
        period_from,
        period_to,
        check_interval_minutes,
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook")
def get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = _build_operations_status_history_compare_payload(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        use_case=use_case,
    )

    current_summary = payload.get("current_period", {}).get("summary", {})
    delta = payload.get("delta", {})

    delta_action_required_days = int(delta.get("action_required_days", 0) or 0)
    delta_warning_days = int(delta.get("warning_days", 0) or 0)
    delta_critical_days = int(delta.get("critical_days", 0) or 0)
    current_critical_days = int(current_summary.get("by_status", {}).get("critical", 0) or 0)
    current_action_required_days = int(current_summary.get("action_required_days", 0) or 0)

    trend = _resolve_operations_status_trend(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
    )
    alert = _resolve_operations_trend_alert(
        delta_action_required_days=delta_action_required_days,
        delta_warning_days=delta_warning_days,
        delta_critical_days=delta_critical_days,
        current_action_required_days=current_action_required_days,
        current_critical_days=current_critical_days,
    )
    status_label = str(alert.get("status", "healthy"))
    priority = _resolve_operations_priority(status_label)
    action_required = status_label in {"warning", "critical"}
    channel = _resolve_operations_notice_dispatch_channel(priority, action_required)
    targets = _resolve_operations_notice_dispatch_targets(channel)
    primary_target = targets[0] if targets else None

    if priority == "high":
        route_decision = "escalate_immediately"
        checklist = [
            "Acionar equipe de incidente imediatamente no canal primário.",
            "Bloquear novos lotes até estabilização dos indicadores.",
            "Registrar RCA preliminar em até 15 minutos.",
        ]
    elif action_required:
        route_decision = "dispatch_primary"
        checklist = [
            "Notificar on-call operacional no canal primário.",
            "Revisar lotes com replay e reduzir batch se necessário.",
            "Confirmar tendência na próxima janela de checagem.",
        ]
    else:
        route_decision = "monitor_only"
        checklist = [
            "Manter monitoramento padrão na cadência definida.",
            "Registrar status saudável no acompanhamento diário.",
        ]

    check_interval_minutes = int(os.getenv("SAAS_AUDIT_OPERATIONS_STATUS_CHECK_INTERVAL_MINUTES", "60"))
    check_interval_minutes = max(5, check_interval_minutes)

    period_from = payload.get("current_period", {}).get("from")
    period_to = payload.get("current_period", {}).get("to")

    return {
        "route_decision": route_decision,
        "channel": channel,
        "primary_target": primary_target,
        "status": status_label,
        "trend": trend,
        "priority": priority,
        "action_required": action_required,
        "checklist": checklist,
        "operation": operation,
        "period": {
            "from": period_from,
            "to": period_to,
        },
        "next_check_in_minutes": check_interval_minutes,
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/export")
def export_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    checklist = payload.get("checklist", [])
    checklist_text = " | ".join(str(item) for item in checklist)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "route_decision",
        "channel",
        "primary_target",
        "status",
        "trend",
        "priority",
        "action_required",
        "operation",
        "period_from",
        "period_to",
        "next_check_in_minutes",
        "checklist",
    ])
    writer.writerow([
        payload.get("route_decision"),
        payload.get("channel"),
        payload.get("primary_target"),
        payload.get("status"),
        payload.get("trend"),
        payload.get("priority"),
        "true" if payload.get("action_required") else "false",
        payload.get("operation"),
        payload.get("period", {}).get("from"),
        payload.get("period", {}).get("to"),
        payload.get("next_check_in_minutes"),
        checklist_text,
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment")
def get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    runbook = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    priority = str(runbook.get("priority", "low"))
    action_required = bool(runbook.get("action_required", False))
    checklist = runbook.get("checklist", [])

    if priority == "high":
        owner = "incident-manager"
        escalation_target = "exec-oncall"
        ack_deadline_minutes = 15
    elif action_required:
        owner = "oncall-ops"
        escalation_target = "ops-manager"
        ack_deadline_minutes = 30
    else:
        owner = "ops-daily"
        escalation_target = None
        ack_deadline_minutes = 0

    return {
        "route_decision": runbook.get("route_decision"),
        "channel": runbook.get("channel"),
        "primary_target": runbook.get("primary_target"),
        "owner": owner,
        "escalation_target": escalation_target,
        "ack_required": action_required,
        "ack_deadline_minutes": ack_deadline_minutes,
        "status": runbook.get("status"),
        "trend": runbook.get("trend"),
        "priority": priority,
        "checklist_size": len(checklist) if isinstance(checklist, list) else 0,
        "operation": runbook.get("operation"),
        "period": runbook.get("period", {}),
        "next_check_in_minutes": runbook.get("next_check_in_minutes"),
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/export")
def export_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "route_decision",
        "channel",
        "primary_target",
        "owner",
        "escalation_target",
        "ack_required",
        "ack_deadline_minutes",
        "status",
        "trend",
        "priority",
        "checklist_size",
        "operation",
        "period_from",
        "period_to",
        "next_check_in_minutes",
    ])
    writer.writerow([
        payload.get("route_decision"),
        payload.get("channel"),
        payload.get("primary_target"),
        payload.get("owner"),
        payload.get("escalation_target"),
        "true" if payload.get("ack_required") else "false",
        payload.get("ack_deadline_minutes"),
        payload.get("status"),
        payload.get("trend"),
        payload.get("priority"),
        payload.get("checklist_size"),
        payload.get("operation"),
        payload.get("period", {}).get("from"),
        payload.get("period", {}).get("to"),
        payload.get("next_check_in_minutes"),
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue")
def get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    assignment = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    priority = str(assignment.get("priority", "low"))
    ack_required = bool(assignment.get("ack_required", False))

    if priority == "high":
        queue_name = "ops-incidents"
        queue_priority = "p1"
    elif ack_required:
        queue_name = "ops-action-required"
        queue_priority = "p2"
    else:
        queue_name = "ops-monitoring"
        queue_priority = "p3"

    return {
        "queue_name": queue_name,
        "queue_priority": queue_priority,
        "owner": assignment.get("owner"),
        "escalation_target": assignment.get("escalation_target"),
        "ack_required": ack_required,
        "ack_deadline_minutes": assignment.get("ack_deadline_minutes"),
        "route_decision": assignment.get("route_decision"),
        "channel": assignment.get("channel"),
        "primary_target": assignment.get("primary_target"),
        "status": assignment.get("status"),
        "trend": assignment.get("trend"),
        "priority": priority,
        "operation": assignment.get("operation"),
        "period": assignment.get("period", {}),
        "next_check_in_minutes": assignment.get("next_check_in_minutes"),
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/export")
def export_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "queue_name",
        "queue_priority",
        "owner",
        "escalation_target",
        "ack_required",
        "ack_deadline_minutes",
        "route_decision",
        "channel",
        "primary_target",
        "status",
        "trend",
        "priority",
        "operation",
        "period_from",
        "period_to",
        "next_check_in_minutes",
    ])
    writer.writerow([
        payload.get("queue_name"),
        payload.get("queue_priority"),
        payload.get("owner"),
        payload.get("escalation_target"),
        "true" if payload.get("ack_required") else "false",
        payload.get("ack_deadline_minutes"),
        payload.get("route_decision"),
        payload.get("channel"),
        payload.get("primary_target"),
        payload.get("status"),
        payload.get("trend"),
        payload.get("priority"),
        payload.get("operation"),
        payload.get("period", {}).get("from"),
        payload.get("period", {}).get("to"),
        payload.get("next_check_in_minutes"),
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket")
def get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    queue_payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    ack_required = bool(queue_payload.get("ack_required", False))
    queue_priority = str(queue_payload.get("queue_priority", "p3"))

    if queue_priority == "p1":
        ticket_severity = "sev1"
    elif queue_priority == "p2":
        ticket_severity = "sev2"
    else:
        ticket_severity = "sev3"

    ticket_type = "incident" if ack_required else "monitoring"
    ticket_state = "open" if ack_required else "queued"

    return {
        "ticket_type": ticket_type,
        "ticket_state": ticket_state,
        "ticket_severity": ticket_severity,
        "queue_name": queue_payload.get("queue_name"),
        "queue_priority": queue_priority,
        "owner": queue_payload.get("owner"),
        "escalation_target": queue_payload.get("escalation_target"),
        "ack_required": ack_required,
        "ack_deadline_minutes": queue_payload.get("ack_deadline_minutes"),
        "route_decision": queue_payload.get("route_decision"),
        "channel": queue_payload.get("channel"),
        "primary_target": queue_payload.get("primary_target"),
        "status": queue_payload.get("status"),
        "trend": queue_payload.get("trend"),
        "priority": queue_payload.get("priority"),
        "operation": queue_payload.get("operation"),
        "period": queue_payload.get("period", {}),
        "next_check_in_minutes": queue_payload.get("next_check_in_minutes"),
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/export")
def export_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ticket_type",
        "ticket_state",
        "ticket_severity",
        "queue_name",
        "queue_priority",
        "owner",
        "escalation_target",
        "ack_required",
        "ack_deadline_minutes",
        "route_decision",
        "channel",
        "primary_target",
        "status",
        "trend",
        "priority",
        "operation",
        "period_from",
        "period_to",
        "next_check_in_minutes",
    ])
    writer.writerow([
        payload.get("ticket_type"),
        payload.get("ticket_state"),
        payload.get("ticket_severity"),
        payload.get("queue_name"),
        payload.get("queue_priority"),
        payload.get("owner"),
        payload.get("escalation_target"),
        "true" if payload.get("ack_required") else "false",
        payload.get("ack_deadline_minutes"),
        payload.get("route_decision"),
        payload.get("channel"),
        payload.get("primary_target"),
        payload.get("status"),
        payload.get("trend"),
        payload.get("priority"),
        payload.get("operation"),
        payload.get("period", {}).get("from"),
        payload.get("period", {}).get("to"),
        payload.get("next_check_in_minutes"),
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla")
def get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    ticket_payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    ack_required = bool(ticket_payload.get("ack_required", False))
    ack_deadline_minutes = int(ticket_payload.get("ack_deadline_minutes", 0) or 0)

    if not ack_required:
        sla_status = "not_required"
        breach_risk = "low"
    elif ack_deadline_minutes <= 15:
        sla_status = "at_risk"
        breach_risk = "high"
    elif ack_deadline_minutes <= 30:
        sla_status = "on_track"
        breach_risk = "medium"
    else:
        sla_status = "on_track"
        breach_risk = "low"

    return {
        "ticket_type": ticket_payload.get("ticket_type"),
        "ticket_state": ticket_payload.get("ticket_state"),
        "ticket_severity": ticket_payload.get("ticket_severity"),
        "queue_name": ticket_payload.get("queue_name"),
        "queue_priority": ticket_payload.get("queue_priority"),
        "owner": ticket_payload.get("owner"),
        "escalation_target": ticket_payload.get("escalation_target"),
        "ack_required": ack_required,
        "ack_deadline_minutes": ack_deadline_minutes,
        "sla_status": sla_status,
        "breach_risk": breach_risk,
        "route_decision": ticket_payload.get("route_decision"),
        "status": ticket_payload.get("status"),
        "trend": ticket_payload.get("trend"),
        "priority": ticket_payload.get("priority"),
        "operation": ticket_payload.get("operation"),
        "period": ticket_payload.get("period", {}),
        "next_check_in_minutes": ticket_payload.get("next_check_in_minutes"),
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/export")
def export_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ticket_type",
        "ticket_state",
        "ticket_severity",
        "queue_name",
        "queue_priority",
        "owner",
        "escalation_target",
        "ack_required",
        "ack_deadline_minutes",
        "sla_status",
        "breach_risk",
        "route_decision",
        "status",
        "trend",
        "priority",
        "operation",
        "period_from",
        "period_to",
        "next_check_in_minutes",
    ])
    writer.writerow([
        payload.get("ticket_type"),
        payload.get("ticket_state"),
        payload.get("ticket_severity"),
        payload.get("queue_name"),
        payload.get("queue_priority"),
        payload.get("owner"),
        payload.get("escalation_target"),
        "true" if payload.get("ack_required") else "false",
        payload.get("ack_deadline_minutes"),
        payload.get("sla_status"),
        payload.get("breach_risk"),
        payload.get("route_decision"),
        payload.get("status"),
        payload.get("trend"),
        payload.get("priority"),
        payload.get("operation"),
        payload.get("period", {}).get("from"),
        payload.get("period", {}).get("to"),
        payload.get("next_check_in_minutes"),
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch")
def get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    sla_status = str(payload.get("sla_status", "not_required"))
    breach_risk = str(payload.get("breach_risk", "low"))
    ack_required = bool(payload.get("ack_required", False))

    if sla_status == "at_risk":
        watch_state = "urgent"
    elif sla_status == "on_track" and breach_risk == "medium":
        watch_state = "attention"
    else:
        watch_state = "normal"

    should_page = ack_required and watch_state in {"urgent", "attention"}

    return {
        "watch_state": watch_state,
        "should_page": should_page,
        "sla_status": sla_status,
        "breach_risk": breach_risk,
        "ticket_type": payload.get("ticket_type"),
        "ticket_state": payload.get("ticket_state"),
        "ticket_severity": payload.get("ticket_severity"),
        "queue_name": payload.get("queue_name"),
        "queue_priority": payload.get("queue_priority"),
        "owner": payload.get("owner"),
        "ack_required": ack_required,
        "ack_deadline_minutes": payload.get("ack_deadline_minutes"),
        "status": payload.get("status"),
        "trend": payload.get("trend"),
        "priority": payload.get("priority"),
        "operation": payload.get("operation"),
        "period": payload.get("period", {}),
        "next_check_in_minutes": payload.get("next_check_in_minutes"),
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/export")
def export_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "watch_state",
        "should_page",
        "sla_status",
        "breach_risk",
        "ticket_type",
        "ticket_state",
        "ticket_severity",
        "queue_name",
        "queue_priority",
        "owner",
        "ack_required",
        "ack_deadline_minutes",
        "status",
        "trend",
        "priority",
        "operation",
        "period_from",
        "period_to",
        "next_check_in_minutes",
    ])
    writer.writerow([
        payload.get("watch_state"),
        "true" if payload.get("should_page") else "false",
        payload.get("sla_status"),
        payload.get("breach_risk"),
        payload.get("ticket_type"),
        payload.get("ticket_state"),
        payload.get("ticket_severity"),
        payload.get("queue_name"),
        payload.get("queue_priority"),
        payload.get("owner"),
        "true" if payload.get("ack_required") else "false",
        payload.get("ack_deadline_minutes"),
        payload.get("status"),
        payload.get("trend"),
        payload.get("priority"),
        payload.get("operation"),
        payload.get("period", {}).get("from"),
        payload.get("period", {}).get("to"),
        payload.get("next_check_in_minutes"),
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary")
def get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    watch_state = str(payload.get("watch_state", "normal"))
    should_page = bool(payload.get("should_page", False))
    next_check_in_minutes = int(payload.get("next_check_in_minutes", 60) or 60)

    if watch_state == "urgent":
        escalation_mode = "immediate"
        follow_up_in_minutes = 5
    elif watch_state == "attention":
        escalation_mode = "expedited"
        follow_up_in_minutes = 15
    else:
        escalation_mode = "routine"
        follow_up_in_minutes = next_check_in_minutes

    return {
        "watch_state": watch_state,
        "should_page": should_page,
        "escalation_mode": escalation_mode,
        "follow_up_in_minutes": follow_up_in_minutes,
        "sla_status": payload.get("sla_status"),
        "breach_risk": payload.get("breach_risk"),
        "ticket_type": payload.get("ticket_type"),
        "ticket_state": payload.get("ticket_state"),
        "ticket_severity": payload.get("ticket_severity"),
        "queue_name": payload.get("queue_name"),
        "queue_priority": payload.get("queue_priority"),
        "owner": payload.get("owner"),
        "ack_required": payload.get("ack_required"),
        "ack_deadline_minutes": payload.get("ack_deadline_minutes"),
        "status": payload.get("status"),
        "trend": payload.get("trend"),
        "priority": payload.get("priority"),
        "operation": payload.get("operation"),
        "period": payload.get("period", {}),
        "next_check_in_minutes": next_check_in_minutes,
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/export")
def export_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "watch_state",
        "should_page",
        "escalation_mode",
        "follow_up_in_minutes",
        "sla_status",
        "breach_risk",
        "ticket_type",
        "ticket_state",
        "ticket_severity",
        "queue_name",
        "queue_priority",
        "owner",
        "ack_required",
        "ack_deadline_minutes",
        "status",
        "trend",
        "priority",
        "operation",
        "period_from",
        "period_to",
        "next_check_in_minutes",
    ])
    writer.writerow([
        payload.get("watch_state"),
        "true" if payload.get("should_page") else "false",
        payload.get("escalation_mode"),
        payload.get("follow_up_in_minutes"),
        payload.get("sla_status"),
        payload.get("breach_risk"),
        payload.get("ticket_type"),
        payload.get("ticket_state"),
        payload.get("ticket_severity"),
        payload.get("queue_name"),
        payload.get("queue_priority"),
        payload.get("owner"),
        "true" if payload.get("ack_required") else "false",
        payload.get("ack_deadline_minutes"),
        payload.get("status"),
        payload.get("trend"),
        payload.get("priority"),
        payload.get("operation"),
        payload.get("period", {}).get("from"),
        payload.get("period", {}).get("to"),
        payload.get("next_check_in_minutes"),
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision")
def get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    watch_state = str(payload.get("watch_state", "normal"))
    should_page = bool(payload.get("should_page", False))

    if watch_state == "urgent":
        decision = "escalate_immediately"
        action = "page_and_war_room"
    elif watch_state == "attention":
        decision = "escalate_follow_up"
        action = "page_and_follow_up"
    else:
        decision = "monitor_routine"
        action = "no_page"

    return {
        "decision": decision,
        "action": action,
        "watch_state": watch_state,
        "should_page": should_page,
        "escalation_mode": payload.get("escalation_mode"),
        "follow_up_in_minutes": payload.get("follow_up_in_minutes"),
        "sla_status": payload.get("sla_status"),
        "breach_risk": payload.get("breach_risk"),
        "ticket_type": payload.get("ticket_type"),
        "ticket_state": payload.get("ticket_state"),
        "ticket_severity": payload.get("ticket_severity"),
        "queue_name": payload.get("queue_name"),
        "queue_priority": payload.get("queue_priority"),
        "owner": payload.get("owner"),
        "ack_required": payload.get("ack_required"),
        "ack_deadline_minutes": payload.get("ack_deadline_minutes"),
        "status": payload.get("status"),
        "trend": payload.get("trend"),
        "priority": payload.get("priority"),
        "operation": payload.get("operation"),
        "period": payload.get("period", {}),
        "next_check_in_minutes": payload.get("next_check_in_minutes"),
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/export")
def export_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "decision",
        "action",
        "watch_state",
        "should_page",
        "escalation_mode",
        "follow_up_in_minutes",
        "sla_status",
        "breach_risk",
        "ticket_type",
        "ticket_state",
        "ticket_severity",
        "queue_name",
        "queue_priority",
        "owner",
        "ack_required",
        "ack_deadline_minutes",
        "status",
        "trend",
        "priority",
        "operation",
        "period_from",
        "period_to",
        "next_check_in_minutes",
    ])
    writer.writerow([
        payload.get("decision"),
        payload.get("action"),
        payload.get("watch_state"),
        "true" if payload.get("should_page") else "false",
        payload.get("escalation_mode"),
        payload.get("follow_up_in_minutes"),
        payload.get("sla_status"),
        payload.get("breach_risk"),
        payload.get("ticket_type"),
        payload.get("ticket_state"),
        payload.get("ticket_severity"),
        payload.get("queue_name"),
        payload.get("queue_priority"),
        payload.get("owner"),
        "true" if payload.get("ack_required") else "false",
        payload.get("ack_deadline_minutes"),
        payload.get("status"),
        payload.get("trend"),
        payload.get("priority"),
        payload.get("operation"),
        payload.get("period", {}).get("from"),
        payload.get("period", {}).get("to"),
        payload.get("next_check_in_minutes"),
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch")
def get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    decision = str(payload.get("decision", "monitor_routine"))
    should_page = bool(payload.get("should_page", False))
    queue_priority = str(payload.get("queue_priority", "p3"))

    if decision == "escalate_immediately":
        dispatch_mode = "war-room"
    elif decision == "escalate_follow_up":
        dispatch_mode = "on-call"
    else:
        dispatch_mode = "routine"

    if should_page:
        notify_channel = "ops-alert"
    elif queue_priority == "p3":
        notify_channel = "ops-daily"
    else:
        notify_channel = "ops-queue"

    return {
        "dispatch_mode": dispatch_mode,
        "notify_channel": notify_channel,
        "decision": decision,
        "action": payload.get("action"),
        "watch_state": payload.get("watch_state"),
        "should_page": should_page,
        "escalation_mode": payload.get("escalation_mode"),
        "follow_up_in_minutes": payload.get("follow_up_in_minutes"),
        "sla_status": payload.get("sla_status"),
        "breach_risk": payload.get("breach_risk"),
        "ticket_type": payload.get("ticket_type"),
        "ticket_state": payload.get("ticket_state"),
        "ticket_severity": payload.get("ticket_severity"),
        "queue_name": payload.get("queue_name"),
        "queue_priority": queue_priority,
        "owner": payload.get("owner"),
        "ack_required": payload.get("ack_required"),
        "ack_deadline_minutes": payload.get("ack_deadline_minutes"),
        "status": payload.get("status"),
        "trend": payload.get("trend"),
        "priority": payload.get("priority"),
        "operation": payload.get("operation"),
        "period": payload.get("period", {}),
        "next_check_in_minutes": payload.get("next_check_in_minutes"),
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/export")
def export_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "dispatch_mode",
        "notify_channel",
        "decision",
        "action",
        "watch_state",
        "should_page",
        "escalation_mode",
        "follow_up_in_minutes",
        "sla_status",
        "breach_risk",
        "ticket_type",
        "ticket_state",
        "ticket_severity",
        "queue_name",
        "queue_priority",
        "owner",
        "ack_required",
        "ack_deadline_minutes",
        "status",
        "trend",
        "priority",
        "operation",
        "period_from",
        "period_to",
        "next_check_in_minutes",
    ])
    writer.writerow([
        payload.get("dispatch_mode"),
        payload.get("notify_channel"),
        payload.get("decision"),
        payload.get("action"),
        payload.get("watch_state"),
        "true" if payload.get("should_page") else "false",
        payload.get("escalation_mode"),
        payload.get("follow_up_in_minutes"),
        payload.get("sla_status"),
        payload.get("breach_risk"),
        payload.get("ticket_type"),
        payload.get("ticket_state"),
        payload.get("ticket_severity"),
        payload.get("queue_name"),
        payload.get("queue_priority"),
        payload.get("owner"),
        "true" if payload.get("ack_required") else "false",
        payload.get("ack_deadline_minutes"),
        payload.get("status"),
        payload.get("trend"),
        payload.get("priority"),
        payload.get("operation"),
        payload.get("period", {}).get("from"),
        payload.get("period", {}).get("to"),
        payload.get("next_check_in_minutes"),
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/receipt")
def get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch_receipt(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    dispatch_mode = str(payload.get("dispatch_mode", "routine"))
    should_page = bool(payload.get("should_page", False))

    if dispatch_mode == "war-room":
        receipt_status = "sent_critical"
    elif should_page:
        receipt_status = "sent_priority"
    else:
        receipt_status = "queued"

    return {
        "receipt_status": receipt_status,
        "dispatch_mode": dispatch_mode,
        "notify_channel": payload.get("notify_channel"),
        "decision": payload.get("decision"),
        "action": payload.get("action"),
        "watch_state": payload.get("watch_state"),
        "should_page": should_page,
        "escalation_mode": payload.get("escalation_mode"),
        "follow_up_in_minutes": payload.get("follow_up_in_minutes"),
        "sla_status": payload.get("sla_status"),
        "breach_risk": payload.get("breach_risk"),
        "ticket_type": payload.get("ticket_type"),
        "ticket_state": payload.get("ticket_state"),
        "ticket_severity": payload.get("ticket_severity"),
        "queue_name": payload.get("queue_name"),
        "queue_priority": payload.get("queue_priority"),
        "owner": payload.get("owner"),
        "ack_required": payload.get("ack_required"),
        "ack_deadline_minutes": payload.get("ack_deadline_minutes"),
        "status": payload.get("status"),
        "trend": payload.get("trend"),
        "priority": payload.get("priority"),
        "operation": payload.get("operation"),
        "period": payload.get("period", {}),
        "next_check_in_minutes": payload.get("next_check_in_minutes"),
    }


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/receipt/export")
def export_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch_receipt_csv(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch_receipt(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "receipt_status",
        "dispatch_mode",
        "notify_channel",
        "decision",
        "action",
        "watch_state",
        "should_page",
        "escalation_mode",
        "follow_up_in_minutes",
        "sla_status",
        "breach_risk",
        "ticket_type",
        "ticket_state",
        "ticket_severity",
        "queue_name",
        "queue_priority",
        "owner",
        "ack_required",
        "ack_deadline_minutes",
        "status",
        "trend",
        "priority",
        "operation",
        "period_from",
        "period_to",
        "next_check_in_minutes",
    ])
    writer.writerow([
        payload.get("receipt_status"),
        payload.get("dispatch_mode"),
        payload.get("notify_channel"),
        payload.get("decision"),
        payload.get("action"),
        payload.get("watch_state"),
        "true" if payload.get("should_page") else "false",
        payload.get("escalation_mode"),
        payload.get("follow_up_in_minutes"),
        payload.get("sla_status"),
        payload.get("breach_risk"),
        payload.get("ticket_type"),
        payload.get("ticket_state"),
        payload.get("ticket_severity"),
        payload.get("queue_name"),
        payload.get("queue_priority"),
        payload.get("owner"),
        "true" if payload.get("ack_required") else "false",
        payload.get("ack_deadline_minutes"),
        payload.get("status"),
        payload.get("trend"),
        payload.get("priority"),
        payload.get("operation"),
        payload.get("period", {}).get("from"),
        payload.get("period", {}).get("to"),
        payload.get("next_check_in_minutes"),
    ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch_receipt.csv"',
        },
    )


@router.get("/audit-events/metrics/operations/status/trend/overview/brief/decision/notice/dispatch/routes/brief/decision/runbook/assignment/queue/ticket/sla/watch/summary/decision/dispatch/receipt/review")
def get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch_receipt_review(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    payload = get_audit_metric_operations_status_trend_overview_brief_decision_notice_dispatch_routes_brief_decision_runbook_assignment_queue_ticket_sla_watch_summary_decision_dispatch_receipt(
        from_date=from_date,
        to_date=to_date,
        operation=operation,
        x_admin_token=x_admin_token,
        use_case=use_case,
    )

    receipt_status = str(payload.get("receipt_status", "queued"))
    should_page = bool(payload.get("should_page", False))

    if receipt_status == "sent_critical":
        review_state = "critical_review"
    elif receipt_status == "sent_priority":
        review_state = "priority_review"
    else:
        review_state = "routine_review"

    review_required = should_page or review_state != "routine_review"

    return {
        "review_state": review_state,
        "review_required": review_required,
        "receipt_status": receipt_status,
        "dispatch_mode": payload.get("dispatch_mode"),
        "notify_channel": payload.get("notify_channel"),
        "decision": payload.get("decision"),
        "action": payload.get("action"),
        "watch_state": payload.get("watch_state"),
        "should_page": should_page,
        "escalation_mode": payload.get("escalation_mode"),
        "follow_up_in_minutes": payload.get("follow_up_in_minutes"),
        "sla_status": payload.get("sla_status"),
        "breach_risk": payload.get("breach_risk"),
        "ticket_type": payload.get("ticket_type"),
        "ticket_state": payload.get("ticket_state"),
        "ticket_severity": payload.get("ticket_severity"),
        "queue_name": payload.get("queue_name"),
        "queue_priority": payload.get("queue_priority"),
        "owner": payload.get("owner"),
        "ack_required": payload.get("ack_required"),
        "ack_deadline_minutes": payload.get("ack_deadline_minutes"),
        "status": payload.get("status"),
        "trend": payload.get("trend"),
        "priority": payload.get("priority"),
        "operation": payload.get("operation"),
        "period": payload.get("period", {}),
        "next_check_in_minutes": payload.get("next_check_in_minutes"),
    }


@router.get("/audit-events/metrics/operations/status/history/export")
def export_audit_metric_operations_status_history_csv(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    operation: str | None = Query(default=None),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    today = date.today()
    start_date = from_date or (today - timedelta(days=6))
    end_date = to_date or today
    _assert_range_limit_or_raise(start_date, end_date)

    warning_threshold = float(os.getenv("SAAS_AUDIT_OPERATIONS_REPLAY_WARNING_THRESHOLD", "0.15"))
    critical_threshold = float(os.getenv("SAAS_AUDIT_OPERATIONS_REPLAY_CRITICAL_THRESHOLD", "0.35"))

    raw_items = use_case.get_admin_audit_metric_operations_metrics_history(
        start_date=start_date,
        end_date=end_date,
        operation=operation,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "date",
        "status",
        "action_required",
        "total_operations",
        "replay_count",
        "replay_ratio",
        "dry_run_count",
        "success_count",
        "total_processed",
        "unique_request_ids",
        "warning_threshold",
        "critical_threshold",
    ])

    for item in raw_items:
        replay_ratio = float(item.get("replay_ratio", 0.0) or 0.0)
        alert = _resolve_operations_replay_alert(
            replay_ratio=replay_ratio,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
        )
        status_label = str(alert.get("status", "healthy"))

        writer.writerow([
            item.get("date"),
            status_label,
            "true" if status_label in {"warning", "critical"} else "false",
            int(item.get("total_operations", 0) or 0),
            int(item.get("replay_count", 0) or 0),
            round(replay_ratio, 4),
            int(item.get("dry_run_count", 0) or 0),
            int(item.get("success_count", 0) or 0),
            int(item.get("total_processed", 0) or 0),
            int(item.get("unique_request_ids", 0) or 0),
            warning_threshold,
            critical_threshold,
        ])

    csv_content = output.getvalue()
    output.close()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saas_audit_metric_operations_status_history.csv"',
        },
    )


@router.get("/audit-events/metrics/status")
def get_audit_metrics_status(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    latest = use_case.get_latest_admin_audit_metrics_snapshot()
    max_age_days = int(os.getenv("SAAS_AUDIT_SNAPSHOT_MAX_AGE_DAYS", "1"))
    max_age_days = max(0, max_age_days)
    today = date.today()

    if latest is None:
        return {
            "status": "missing",
            "freshness": {
                "max_age_days": max_age_days,
                "age_days": None,
                "is_fresh": False,
            },
            "latest_snapshot": None,
            "today": today.isoformat(),
        }

    snapshot_date = date.fromisoformat(str(latest.get("snapshot_date")))
    age_days = max(0, (today - snapshot_date).days)
    is_fresh = age_days <= max_age_days

    return {
        "status": "fresh" if is_fresh else "stale",
        "freshness": {
            "max_age_days": max_age_days,
            "age_days": age_days,
            "is_fresh": is_fresh,
        },
        "latest_snapshot": latest,
        "today": today.isoformat(),
    }


@router.post("/audit-events/metrics/backfill")
def backfill_audit_metrics_snapshots(
    request: Request,
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    batch_size: int | None = Query(default=None, ge=1, le=200),
    summary_only: bool = Query(default=False, alias="summary_only"),
    request_id: str | None = Query(default=None, alias="request_id"),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)
    client_ip = request.client.host if request.client else "unknown"

    _assert_range_limit_or_raise(from_date, to_date)
    resolved_batch_size = _resolve_batch_size(batch_size)

    idempotency_key = None
    if request_id:
        idempotency_key = _build_operation_idempotency_key(
            operation="backfill",
            request_id=request_id,
            payload={
                "from": from_date.isoformat(),
                "to": to_date.isoformat(),
                "batch_size": resolved_batch_size,
                "summary_only": summary_only,
            },
        )
        cached = _try_get_cached_idempotent_response(use_case, idempotency_key)
        if cached is not None:
            replay_response = {
                **cached,
                "request_id": request_id,
                "idempotent_replay": True,
            }
            _audit_snapshot_operation(
                client_ip=client_ip,
                operation="backfill",
                outcome="replay",
                created=int(replay_response.get("created", 0) or 0),
                reason=_build_snapshot_operation_reason(
                    operation="backfill",
                    request_id=request_id,
                    from_date=from_date,
                    to_date=to_date,
                    batch_size=resolved_batch_size,
                    summary_only=summary_only,
                    dry_run=False,
                ),
            )
            return {
                **replay_response,
            }

    warning_threshold = float(os.getenv("SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD", "0.2"))
    critical_threshold = float(os.getenv("SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD", "0.5"))

    current_day = from_date
    items: list[dict] = []
    batches: list[dict] = []
    batch_index = 1

    while current_day <= to_date:
        batch_start = current_day
        batch_created_dates: list[str] = []
        batch_created_count = 0

        while current_day <= to_date and batch_created_count < resolved_batch_size:
            metrics = use_case.get_admin_audit_metrics(start_date=current_day, end_date=current_day)
            current_ratio = float(metrics.get("rate_limited", {}).get("ratio", 0.0) or 0.0)
            alert = _resolve_alert(
                current_ratio=current_ratio,
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
            )
            snapshot = use_case.create_admin_audit_metrics_snapshot(
                snapshot_date=current_day,
                start_date=current_day,
                end_date=current_day,
                warning_threshold=float(alert["warning_threshold"]),
                critical_threshold=float(alert["critical_threshold"]),
                alert_status=str(alert["status"]),
            )
            items.append(snapshot)
            batch_created_dates.append(snapshot.get("snapshot_date"))
            batch_created_count += 1
            current_day += timedelta(days=1)

        if batch_created_dates:
            batches.append(
                {
                    "batch": batch_index,
                    "from": batch_start.isoformat(),
                    "to": batch_created_dates[-1],
                    "created": batch_created_count,
                    "created_dates": batch_created_dates,
                }
            )
            batch_index += 1

    response = {
        "created": len(items),
        "batch_size": resolved_batch_size,
        "summary_only": summary_only,
        "period": {
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
        },
    }

    if summary_only:
        response["batches"] = [
            {
                "batch": batch["batch"],
                "from": batch["from"],
                "to": batch["to"],
                "created": batch["created"],
            }
            for batch in batches
        ]
        response["omitted_items"] = len(items)
    else:
        response["batches"] = batches
        response["items"] = items

    if request_id:
        _try_set_cached_idempotent_response(use_case, idempotency_key, response)
        response["request_id"] = request_id
        response["idempotent_replay"] = False

    _audit_snapshot_operation(
        client_ip=client_ip,
        operation="backfill",
        outcome="success",
        created=int(response.get("created", 0) or 0),
        reason=_build_snapshot_operation_reason(
            operation="backfill",
            request_id=request_id,
            from_date=from_date,
            to_date=to_date,
            batch_size=resolved_batch_size,
            summary_only=summary_only,
            dry_run=False,
        ),
    )

    return response


@router.get("/audit-events/metrics/gaps")
def get_audit_metrics_snapshot_gaps(
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)

    _assert_range_limit_or_raise(from_date, to_date)

    return use_case.get_admin_audit_snapshot_gaps(
        start_date=from_date,
        end_date=to_date,
    )


@router.post("/audit-events/metrics/repair")
def repair_audit_metrics_snapshot_gaps(
    request: Request,
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    dry_run: bool = Query(default=False, alias="dry_run"),
    batch_size: int | None = Query(default=None, ge=1, le=200),
    summary_only: bool = Query(default=False, alias="summary_only"),
    request_id: str | None = Query(default=None, alias="request_id"),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    _assert_admin_token_or_raise(x_admin_token)
    client_ip = request.client.host if request.client else "unknown"

    _assert_range_limit_or_raise(from_date, to_date)
    resolved_batch_size = _resolve_batch_size(batch_size)

    idempotency_key = None
    if request_id:
        idempotency_key = _build_operation_idempotency_key(
            operation="repair",
            request_id=request_id,
            payload={
                "from": from_date.isoformat(),
                "to": to_date.isoformat(),
                "dry_run": dry_run,
                "batch_size": resolved_batch_size,
                "summary_only": summary_only,
            },
        )
        cached = _try_get_cached_idempotent_response(use_case, idempotency_key)
        if cached is not None:
            replay_response = {
                **cached,
                "request_id": request_id,
                "idempotent_replay": True,
            }
            _audit_snapshot_operation(
                client_ip=client_ip,
                operation="repair",
                outcome="replay",
                created=int(replay_response.get("created", 0) or 0),
                reason=_build_snapshot_operation_reason(
                    operation="repair",
                    request_id=request_id,
                    from_date=from_date,
                    to_date=to_date,
                    batch_size=resolved_batch_size,
                    summary_only=summary_only,
                    dry_run=dry_run,
                ),
            )
            return {
                **replay_response,
            }

    warning_threshold = float(os.getenv("SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD", "0.2"))
    critical_threshold = float(os.getenv("SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD", "0.5"))

    gaps_before = use_case.get_admin_audit_snapshot_gaps(start_date=from_date, end_date=to_date)
    missing_dates = [date.fromisoformat(item) for item in gaps_before.get("missing_dates", [])]

    if dry_run:
        response = {
            "scanned_period": {
                "from": from_date.isoformat(),
                "to": to_date.isoformat(),
            },
            "dry_run": True,
            "batch_size": resolved_batch_size,
            "summary_only": summary_only,
            "missing_before": gaps_before.get("missing_count", 0),
            "planned": len(missing_dates),
            "planned_dates": [item.isoformat() for item in missing_dates],
            "created": 0,
            "missing_after": gaps_before.get("missing_count", 0),
        }
        if request_id:
            _try_set_cached_idempotent_response(use_case, idempotency_key, response)
            response["request_id"] = request_id
            response["idempotent_replay"] = False

        _audit_snapshot_operation(
            client_ip=client_ip,
            operation="repair",
            outcome="dry_run",
            created=0,
            reason=_build_snapshot_operation_reason(
                operation="repair",
                request_id=request_id,
                from_date=from_date,
                to_date=to_date,
                batch_size=resolved_batch_size,
                summary_only=summary_only,
                dry_run=True,
            ),
        )
        return response

    created_items: list[dict] = []
    batches: list[dict] = []
    batch_index = 1
    for start in range(0, len(missing_dates), resolved_batch_size):
        batch_days = missing_dates[start:start + resolved_batch_size]
        batch_created_dates: list[str] = []

        for missing_day in batch_days:
            metrics = use_case.get_admin_audit_metrics(start_date=missing_day, end_date=missing_day)
            current_ratio = float(metrics.get("rate_limited", {}).get("ratio", 0.0) or 0.0)
            alert = _resolve_alert(
                current_ratio=current_ratio,
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
            )
            snapshot = use_case.create_admin_audit_metrics_snapshot(
                snapshot_date=missing_day,
                start_date=missing_day,
                end_date=missing_day,
                warning_threshold=float(alert["warning_threshold"]),
                critical_threshold=float(alert["critical_threshold"]),
                alert_status=str(alert["status"]),
            )
            created_items.append(snapshot)
            batch_created_dates.append(snapshot.get("snapshot_date"))

        if batch_created_dates:
            batches.append(
                {
                    "batch": batch_index,
                    "from": batch_created_dates[0],
                    "to": batch_created_dates[-1],
                    "created": len(batch_created_dates),
                    "created_dates": batch_created_dates,
                }
            )
            batch_index += 1

    gaps_after = use_case.get_admin_audit_snapshot_gaps(start_date=from_date, end_date=to_date)

    response = {
        "scanned_period": {
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
        },
        "dry_run": False,
        "batch_size": resolved_batch_size,
        "summary_only": summary_only,
        "missing_before": gaps_before.get("missing_count", 0),
        "created": len(created_items),
        "missing_after": gaps_after.get("missing_count", 0),
    }

    if summary_only:
        response["batches"] = [
            {
                "batch": batch["batch"],
                "from": batch["from"],
                "to": batch["to"],
                "created": batch["created"],
            }
            for batch in batches
        ]
        response["omitted_created_dates"] = len(created_items)
    else:
        response["created_dates"] = [item.get("snapshot_date") for item in created_items]
        response["batches"] = batches

    if request_id:
        _try_set_cached_idempotent_response(use_case, idempotency_key, response)
        response["request_id"] = request_id
        response["idempotent_replay"] = False

    _audit_snapshot_operation(
        client_ip=client_ip,
        operation="repair",
        outcome="success",
        created=int(response.get("created", 0) or 0),
        reason=_build_snapshot_operation_reason(
            operation="repair",
            request_id=request_id,
            from_date=from_date,
            to_date=to_date,
            batch_size=resolved_batch_size,
            summary_only=summary_only,
            dry_run=False,
        ),
    )

    return response


@router.post("/cache/invalidate")
def invalidate_cache(
    request: Request,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    x_hotel_id: str | None = Header(default=None, alias="X-Hotel-Id"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
):
    client_ip = request.client.host if request.client else "unknown"

    try:
        _assert_admin_token_or_raise(x_admin_token)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            _audit_cache_invalidate(client_ip, outcome="rejected", reason="token_not_configured")
        elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
            _audit_cache_invalidate(client_ip, outcome="rejected", reason="missing_header")
        elif exc.status_code == status.HTTP_403_FORBIDDEN:
            _audit_cache_invalidate(client_ip, outcome="rejected", reason="invalid_token")
        raise

    rate_limit = int(os.getenv("SAAS_CACHE_INVALIDATE_RATE_LIMIT", "5"))
    rate_window_seconds = int(os.getenv("SAAS_CACHE_INVALIDATE_RATE_WINDOW_SECONDS", "60"))
    identifier = client_ip
    allowed, retry_after = GetSaaSDashboardUseCase.check_cache_invalidate_rate_limit(
        use_case.cache_repository,
        identifier=identifier,
        limit=rate_limit,
        window_seconds=rate_window_seconds,
    )
    if not allowed:
        _audit_cache_invalidate(
            client_ip,
            outcome="rate_limited",
            retry_after=retry_after,
            reason="rate_limit_exceeded",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for cache invalidation",
            headers={"Retry-After": str(retry_after or rate_window_seconds)},
        )

    deleted_keys = GetSaaSDashboardUseCase.invalidate_analytics_cache(
        use_case.cache_repository,
        hotel_id=x_hotel_id,
    )
    _audit_cache_invalidate(client_ip, outcome="success", deleted_keys=deleted_keys)
    return {
        "deleted_keys": deleted_keys,
    }


@router.get("/kpis")
def get_kpis(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    source: str | None = Query(default=None),
    status: str | None = Query(default=None),
    granularity: str | None = Query(default="day"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
    user: UserModel = Depends(get_current_user),
    x_hotel_id: str | None = Header(default=None, alias="X-Hotel-Id"),
):
    effective_hotel_id = _resolve_effective_hotel_id(user, x_hotel_id)
    if not effective_hotel_id:
        raise HTTPException(status_code=403, detail="Usuário sem hotel associado")

    return use_case.get_kpis(
        effective_hotel_id,
        from_date,
        to_date,
        source=source,
        status=status,
        granularity=granularity,
    )


@router.get("/leads")
def get_leads(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    status: str | None = Query(default=None),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
    user: UserModel = Depends(get_current_user),
    x_hotel_id: str | None = Header(default=None, alias="X-Hotel-Id"),
):
    """
    Lista leads do funil SaaS.

    - Usuários comuns usam sempre `user.hotel_id` do token.
    - Super admins (roles administrativos) podem escolher o hotel via header `X-Hotel-Id`.
    """
    effective_hotel_id = _resolve_effective_hotel_id(user, x_hotel_id)
    if not effective_hotel_id:
        raise HTTPException(status_code=403, detail="Usuário sem hotel associado")

    return {
        "items": use_case.get_leads(effective_hotel_id, from_date, to_date, status),
    }


@router.get("/funnel")
def get_funnel(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
    user: UserModel = Depends(get_current_user),
    x_hotel_id: str | None = Header(default=None, alias="X-Hotel-Id"),
):
    effective_hotel_id = _resolve_effective_hotel_id(user, x_hotel_id)
    if not effective_hotel_id:
        raise HTTPException(status_code=403, detail="Usuário sem hotel associado")

    return use_case.get_funnel(effective_hotel_id, from_date, to_date)


@router.get("/funnel/journey")
def get_funnel_journey(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    use_case: GetJourneyFunnelUseCase = Depends(get_journey_funnel_use_case),
    user: UserModel = Depends(get_current_user),
    x_hotel_id: str | None = Header(default=None, alias="X-Hotel-Id"),
):
    """Journey funnel: Lead → Reserva → Confirmada → Check-in → Check-out."""
    effective_hotel_id = _resolve_effective_hotel_id(user, x_hotel_id)
    if not effective_hotel_id:
        raise HTTPException(status_code=403, detail="Usuário sem hotel associado")

    return use_case.execute(
        hotel_id=effective_hotel_id, from_date=from_date, to_date=to_date
    )


@router.get("/timeseries")
def get_timeseries(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    source: str | None = Query(default=None),
    status: str | None = Query(default=None),
    granularity: str | None = Query(default="day"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
    user: UserModel = Depends(get_current_user),
    x_hotel_id: str | None = Header(default=None, alias="X-Hotel-Id"),
):
    effective_hotel_id = _resolve_effective_hotel_id(user, x_hotel_id)
    if not effective_hotel_id:
        raise HTTPException(status_code=403, detail="Usuário sem hotel associado")

    return use_case.get_timeseries(
        effective_hotel_id,
        from_date,
        to_date,
        source=source,
        status=status,
        granularity=granularity,
    )


@router.get("/kpis/compare")
def get_kpis_comparison(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    source: str | None = Query(default=None),
    status: str | None = Query(default=None),
    granularity: str | None = Query(default="day"),
    use_case: GetSaaSDashboardUseCase = Depends(get_saas_dashboard_use_case),
    user: UserModel = Depends(get_current_user),
    x_hotel_id: str | None = Header(default=None, alias="X-Hotel-Id"),
):
    effective_hotel_id = _resolve_effective_hotel_id(user, x_hotel_id)
    if not effective_hotel_id:
        raise HTTPException(status_code=403, detail="Usuário sem hotel associado")

    return use_case.get_kpis_comparison(
        effective_hotel_id,
        from_date,
        to_date,
        source=source,
        status=status,
        granularity=granularity,
    )
