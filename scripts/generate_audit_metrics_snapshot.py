"""Generate daily SaaS audit metrics snapshot (phase 2.19)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.application.use_cases.get_saas_dashboard import GetSaaSDashboardUseCase
from app.infrastructure.cache.redis_repository import RedisRepository
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.saas_repository_sql import SaaSRepositorySQL


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    return date.fromisoformat(raw)


def _resolve_alert(current_ratio: float, warning_threshold: float, critical_threshold: float) -> dict:
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


def _assert_range_limit(from_date: date, to_date: date) -> tuple[bool, str | None]:
    if to_date < from_date:
        return False, "end date must be greater than or equal to start date"

    max_range_days = int(os.getenv("SAAS_AUDIT_SNAPSHOT_MAX_RANGE_DAYS", "90"))
    max_range_days = max(1, max_range_days)
    total_days = (to_date - from_date).days + 1
    if total_days > max_range_days:
        return False, f"date range too large: {total_days} days (max {max_range_days})"

    return True, None


def _resolve_batch_size(raw_batch_size: int | None) -> int:
    default_batch_size = int(os.getenv("SAAS_AUDIT_SNAPSHOT_BATCH_SIZE", "30"))
    default_batch_size = max(1, default_batch_size)
    resolved = int(raw_batch_size or default_batch_size)
    return max(1, min(200, resolved))


def _operation_idempotency_ttl_seconds() -> int:
    ttl = int(os.getenv("SAAS_AUDIT_OPERATION_IDEMPOTENCY_TTL_SECONDS", "86400"))
    return max(60, ttl)


def _build_operation_idempotency_key(operation: str, request_id: str, payload: dict) -> str:
    normalized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"saas:audit_ops:idempotency:{operation}:{request_id}:{digest}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate SaaS audit metrics daily snapshot")
    parser.add_argument("--date", dest="snapshot_date", help="Snapshot date (YYYY-MM-DD)")
    parser.add_argument("--from", dest="from_date", help="Metrics period start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="to_date", help="Metrics period end date (YYYY-MM-DD)")
    parser.add_argument("--backfill-from", dest="backfill_from", help="Backfill start date (YYYY-MM-DD)")
    parser.add_argument("--backfill-to", dest="backfill_to", help="Backfill end date (YYYY-MM-DD)")
    parser.add_argument("--gaps-from", dest="gaps_from", help="Gap detection start date (YYYY-MM-DD)")
    parser.add_argument("--gaps-to", dest="gaps_to", help="Gap detection end date (YYYY-MM-DD)")
    parser.add_argument("--repair-from", dest="repair_from", help="Gap repair start date (YYYY-MM-DD)")
    parser.add_argument("--repair-to", dest="repair_to", help="Gap repair end date (YYYY-MM-DD)")
    parser.add_argument("--repair-dry-run", dest="repair_dry_run", action="store_true", help="Simulate repair without writing snapshots")
    parser.add_argument("--batch-size", dest="batch_size", type=int, help="Chunk size for backfill/repair operations")
    parser.add_argument("--summary-only", dest="summary_only", action="store_true", help="Return compact payload for backfill/repair operations")
    parser.add_argument("--request-id", dest="request_id", help="Optional idempotency key for backfill/repair operations")
    args = parser.parse_args()

    target_date = _parse_date(args.snapshot_date) or date.today()
    start_date = _parse_date(args.from_date) or target_date
    end_date = _parse_date(args.to_date) or target_date

    warning_threshold = float(os.getenv("SAAS_AUDIT_RATE_LIMIT_WARNING_THRESHOLD", "0.2"))
    critical_threshold = float(os.getenv("SAAS_AUDIT_RATE_LIMIT_CRITICAL_THRESHOLD", "0.5"))
    resolved_batch_size = _resolve_batch_size(args.batch_size)

    session = SessionLocal()
    try:
        cache_repository = None
        try:
            cache_repository = RedisRepository()
        except Exception:
            cache_repository = None

        use_case = GetSaaSDashboardUseCase(
            saas_repository=SaaSRepositorySQL(session),
            cache_repository=cache_repository,
            cache_ttl_seconds=120,
        )

        gaps_from = _parse_date(args.gaps_from)
        gaps_to = _parse_date(args.gaps_to)
        if gaps_from or gaps_to:
            if not gaps_from or not gaps_to:
                print(json.dumps({"ok": False, "error": "Both --gaps-from and --gaps-to are required"}))
                return 2
            valid_range, range_error = _assert_range_limit(gaps_from, gaps_to)
            if not valid_range:
                print(json.dumps({"ok": False, "error": range_error}))
                return 2

            gaps = use_case.get_admin_audit_snapshot_gaps(
                start_date=gaps_from,
                end_date=gaps_to,
            )
            print(
                json.dumps(
                    {
                        "ok": True,
                        "mode": "gaps",
                        **gaps,
                    },
                    ensure_ascii=False,
                )
            )
            return 0

        repair_from = _parse_date(args.repair_from)
        repair_to = _parse_date(args.repair_to)
        if repair_from or repair_to:
            if not repair_from or not repair_to:
                print(json.dumps({"ok": False, "error": "Both --repair-from and --repair-to are required"}))
                return 2
            valid_range, range_error = _assert_range_limit(repair_from, repair_to)
            if not valid_range:
                print(json.dumps({"ok": False, "error": range_error}))
                return 2

            repair_idempotency_key = None
            if args.request_id:
                repair_idempotency_key = _build_operation_idempotency_key(
                    operation="repair",
                    request_id=args.request_id,
                    payload={
                        "from": repair_from.isoformat(),
                        "to": repair_to.isoformat(),
                        "dry_run": args.repair_dry_run,
                        "batch_size": resolved_batch_size,
                        "summary_only": args.summary_only,
                    },
                )
                if cache_repository is not None:
                    try:
                        cached = cache_repository.get(repair_idempotency_key)
                        if cached is not None:
                            print(json.dumps({**cached, "request_id": args.request_id, "idempotent_replay": True}, ensure_ascii=False))
                            return 0
                    except Exception:
                        pass

            gaps_before = use_case.get_admin_audit_snapshot_gaps(
                start_date=repair_from,
                end_date=repair_to,
            )
            missing_days = [date.fromisoformat(raw) for raw in gaps_before.get("missing_dates", [])]

            if args.repair_dry_run:
                response = {
                    "ok": True,
                    "mode": "repair",
                    "summary_only": args.summary_only,
                    "dry_run": True,
                    "batch_size": resolved_batch_size,
                    "from": repair_from.isoformat(),
                    "to": repair_to.isoformat(),
                    "missing_before": gaps_before.get("missing_count", 0),
                    "planned": len(missing_days),
                    "planned_dates": [day.isoformat() for day in missing_days],
                    "created": 0,
                    "missing_after": gaps_before.get("missing_count", 0),
                }
                if args.request_id:
                    response["request_id"] = args.request_id
                    response["idempotent_replay"] = False
                    if cache_repository is not None and repair_idempotency_key is not None:
                        try:
                            cache_repository.set(repair_idempotency_key, response, ttl_seconds=_operation_idempotency_ttl_seconds())
                        except Exception:
                            pass
                print(json.dumps(response, ensure_ascii=False))
                return 0

            created = []
            batches: list[dict] = []
            batch_index = 1
            for start in range(0, len(missing_days), resolved_batch_size):
                batch_days = missing_days[start:start + resolved_batch_size]
                batch_created_dates: list[str] = []
                for missing_day in batch_days:
                    metrics = use_case.get_admin_audit_metrics(start_date=missing_day, end_date=missing_day)
                    current_ratio = float(metrics.get("rate_limited", {}).get("ratio", 0.0) or 0.0)
                    alert = _resolve_alert(current_ratio, warning_threshold, critical_threshold)
                    snapshot = use_case.create_admin_audit_metrics_snapshot(
                        snapshot_date=missing_day,
                        start_date=missing_day,
                        end_date=missing_day,
                        warning_threshold=float(alert["warning_threshold"]),
                        critical_threshold=float(alert["critical_threshold"]),
                        alert_status=str(alert["status"]),
                    )
                    created.append(snapshot)
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

            gaps_after = use_case.get_admin_audit_snapshot_gaps(
                start_date=repair_from,
                end_date=repair_to,
            )
            response = (
                {
                    "ok": True,
                    "mode": "repair",
                    "summary_only": True,
                    "batch_size": resolved_batch_size,
                    "from": repair_from.isoformat(),
                    "to": repair_to.isoformat(),
                    "missing_before": gaps_before.get("missing_count", 0),
                    "created": len(created),
                    "batches": [
                        {
                            "batch": batch["batch"],
                            "from": batch["from"],
                            "to": batch["to"],
                            "created": batch["created"],
                        }
                        for batch in batches
                    ],
                    "omitted_created_dates": len(created),
                    "missing_after": gaps_after.get("missing_count", 0),
                }
                if args.summary_only
                else {
                    "ok": True,
                    "mode": "repair",
                    "summary_only": False,
                    "batch_size": resolved_batch_size,
                    "from": repair_from.isoformat(),
                    "to": repair_to.isoformat(),
                    "missing_before": gaps_before.get("missing_count", 0),
                    "created": len(created),
                    "created_dates": [item.get("snapshot_date") for item in created],
                    "batches": batches,
                    "missing_after": gaps_after.get("missing_count", 0),
                }
            )
            if args.request_id:
                response["request_id"] = args.request_id
                response["idempotent_replay"] = False
                if cache_repository is not None and repair_idempotency_key is not None:
                    try:
                        cache_repository.set(repair_idempotency_key, response, ttl_seconds=_operation_idempotency_ttl_seconds())
                    except Exception:
                        pass
            print(json.dumps(response, ensure_ascii=False))
            return 0

        backfill_from = _parse_date(args.backfill_from)
        backfill_to = _parse_date(args.backfill_to)
        if backfill_from or backfill_to:
            if not backfill_from or not backfill_to:
                print(json.dumps({"ok": False, "error": "Both --backfill-from and --backfill-to are required"}))
                return 2
            valid_range, range_error = _assert_range_limit(backfill_from, backfill_to)
            if not valid_range:
                print(json.dumps({"ok": False, "error": range_error}))
                return 2

            backfill_idempotency_key = None
            if args.request_id:
                backfill_idempotency_key = _build_operation_idempotency_key(
                    operation="backfill",
                    request_id=args.request_id,
                    payload={
                        "from": backfill_from.isoformat(),
                        "to": backfill_to.isoformat(),
                        "batch_size": resolved_batch_size,
                        "summary_only": args.summary_only,
                    },
                )
                if cache_repository is not None:
                    try:
                        cached = cache_repository.get(backfill_idempotency_key)
                        if cached is not None:
                            print(json.dumps({**cached, "request_id": args.request_id, "idempotent_replay": True}, ensure_ascii=False))
                            return 0
                    except Exception:
                        pass

            items = []
            batches: list[dict] = []
            batch_index = 1
            current_day = backfill_from
            while current_day <= backfill_to:
                batch_start = current_day
                batch_created_dates: list[str] = []
                batch_created_count = 0
                while current_day <= backfill_to and batch_created_count < resolved_batch_size:
                    metrics = use_case.get_admin_audit_metrics(start_date=current_day, end_date=current_day)
                    current_ratio = float(metrics.get("rate_limited", {}).get("ratio", 0.0) or 0.0)
                    alert = _resolve_alert(current_ratio, warning_threshold, critical_threshold)
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
                    current_day = date.fromordinal(current_day.toordinal() + 1)

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

            response = (
                {
                    "ok": True,
                    "mode": "backfill",
                    "summary_only": True,
                    "batch_size": resolved_batch_size,
                    "from": backfill_from.isoformat(),
                    "to": backfill_to.isoformat(),
                    "created": len(items),
                    "batches": [
                        {
                            "batch": batch["batch"],
                            "from": batch["from"],
                            "to": batch["to"],
                            "created": batch["created"],
                        }
                        for batch in batches
                    ],
                    "omitted_items": len(items),
                }
                if args.summary_only
                else {
                    "ok": True,
                    "mode": "backfill",
                    "summary_only": False,
                    "batch_size": resolved_batch_size,
                    "from": backfill_from.isoformat(),
                    "to": backfill_to.isoformat(),
                    "created": len(items),
                    "batches": batches,
                    "items": items,
                }
            )
            if args.request_id:
                response["request_id"] = args.request_id
                response["idempotent_replay"] = False
                if cache_repository is not None and backfill_idempotency_key is not None:
                    try:
                        cache_repository.set(backfill_idempotency_key, response, ttl_seconds=_operation_idempotency_ttl_seconds())
                    except Exception:
                        pass
            print(json.dumps(response, ensure_ascii=False))
            return 0

        metrics = use_case.get_admin_audit_metrics(start_date=start_date, end_date=end_date)
        current_ratio = float(metrics.get("rate_limited", {}).get("ratio", 0.0) or 0.0)
        alert = _resolve_alert(current_ratio, warning_threshold, critical_threshold)

        snapshot = use_case.create_admin_audit_metrics_snapshot(
            snapshot_date=target_date,
            start_date=start_date,
            end_date=end_date,
            warning_threshold=float(alert["warning_threshold"]),
            critical_threshold=float(alert["critical_threshold"]),
            alert_status=str(alert["status"]),
        )

        print(
            json.dumps(
                {
                    "ok": True,
                    "snapshot": snapshot,
                    "alert": alert,
                    "period": {
                        "from": start_date.isoformat(),
                        "to": end_date.isoformat(),
                    },
                },
                ensure_ascii=False,
            )
        )
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
