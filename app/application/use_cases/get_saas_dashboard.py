from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from typing import Any

from app.domain.repositories.cache_repository import CacheRepository


class GetSaaSDashboardUseCase:
    CACHE_KEY_PREFIX = "saas:dashboard"
    CACHE_INVALIDATE_RL_PREFIX = "saas:cache_invalidate:rl"

    def __init__(
        self,
        saas_repository,
        cache_repository: CacheRepository | None = None,
        cache_ttl_seconds: int = 120,
    ):
        self.saas_repository = saas_repository
        self.cache_repository = cache_repository
        self.cache_ttl_seconds = cache_ttl_seconds

    def _cache_key(self, operation: str, params: dict[str, Any]) -> str:
        hotel_id = params.get("hotel_id") or "global"
        normalized = json.dumps(params, sort_keys=True, default=str, ensure_ascii=False)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"{self.CACHE_KEY_PREFIX}:hotel:{hotel_id}:{operation}:{digest}"

    @classmethod
    def invalidate_analytics_cache(
        cls,
        cache_repository: CacheRepository | None,
        hotel_id: str | None = None,
    ) -> int:
        if cache_repository is None:
            return 0

        client = getattr(cache_repository, "client", None)
        if client is None:
            return 0

        deleted = 0
        pattern = f"{cls.CACHE_KEY_PREFIX}:*" if not hotel_id else f"{cls.CACHE_KEY_PREFIX}:hotel:{hotel_id}:*"
        try:
            for key in client.scan_iter(match=pattern):
                normalized_key = key.decode("utf-8") if isinstance(key, bytes) else str(key)
                cache_repository.delete(normalized_key)
                deleted += 1
        except Exception:
            return 0

        return deleted

    @classmethod
    def check_cache_invalidate_rate_limit(
        cls,
        cache_repository: CacheRepository | None,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int | None]:
        if cache_repository is None or limit <= 0 or window_seconds <= 0:
            return True, None

        client = getattr(cache_repository, "client", None)
        if client is None:
            return True, None

        normalized_identifier = "".join(ch if ch.isalnum() or ch in {"-", "_", ":", "."} else "_" for ch in (identifier or "unknown"))
        key = f"{cls.CACHE_INVALIDATE_RL_PREFIX}:{normalized_identifier}"

        try:
            current = int(client.incr(key))
            if current == 1:
                client.expire(key, window_seconds)

            if current > limit:
                retry_after = int(client.ttl(key))
                return False, retry_after if retry_after > 0 else window_seconds
        except Exception:
            return True, None

        return True, None

    def _get_cached_or_compute(
        self,
        operation: str,
        params: dict[str, Any],
        compute,
    ):
        if not self.cache_repository:
            return compute()

        key = self._cache_key(operation, params)
        try:
            cached = self.cache_repository.get(key)
            if cached is not None:
                return cached
        except Exception:
            pass

        value = compute()
        try:
            self.cache_repository.set(key, value, ttl_seconds=self.cache_ttl_seconds)
        except Exception:
            pass
        return value

    def get_kpis(
        self,
        hotel_id: str,
        start_date: date | None,
        end_date: date | None,
        source: str | None = None,
        status: str | None = None,
        granularity: str | None = None,
    ) -> dict[str, Any]:
        params = {
            "hotel_id": hotel_id,
            "start_date": start_date,
            "end_date": end_date,
            "source": source,
            "status": status,
            "granularity": granularity,
        }
        return self._get_cached_or_compute(
            operation="kpis",
            params=params,
            compute=lambda: self.saas_repository.get_kpis(
                hotel_id,
                start_date,
                end_date,
                source=source,
                status=status,
                granularity=granularity,
            ),
        )

    def get_leads(
        self,
        hotel_id: str,
        start_date: date | None,
        end_date: date | None,
        status: str | None,
    ) -> list[dict[str, Any]]:
        params = {
            "hotel_id": hotel_id,
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
        }
        return self._get_cached_or_compute(
            operation="leads",
            params=params,
            compute=lambda: self.saas_repository.list_leads(hotel_id, start_date, end_date, status),
        )

    def get_funnel(
        self,
        hotel_id: str,
        start_date: date | None,
        end_date: date | None,
    ) -> dict[str, Any]:
        params = {
            "hotel_id": hotel_id,
            "start_date": start_date,
            "end_date": end_date,
        }
        return self._get_cached_or_compute(
            operation="funnel",
            params=params,
            compute=lambda: self.saas_repository.get_funnel(hotel_id, start_date, end_date),
        )

    def get_timeseries(
        self,
        hotel_id: str,
        start_date: date | None,
        end_date: date | None,
        source: str | None = None,
        status: str | None = None,
        granularity: str | None = None,
    ) -> dict[str, Any]:
        params = {
            "hotel_id": hotel_id,
            "start_date": start_date,
            "end_date": end_date,
            "source": source,
            "status": status,
            "granularity": granularity,
        }
        return self._get_cached_or_compute(
            operation="timeseries",
            params=params,
            compute=lambda: self.saas_repository.get_timeseries(
                hotel_id,
                start_date,
                end_date,
                source=source,
                status=status,
                granularity=granularity,
            ),
        )

    def get_kpis_comparison(
        self,
        hotel_id: str,
        start_date: date | None,
        end_date: date | None,
        source: str | None = None,
        status: str | None = None,
        granularity: str | None = None,
    ) -> dict[str, Any]:
        params = {
            "hotel_id": hotel_id,
            "start_date": start_date,
            "end_date": end_date,
            "source": source,
            "status": status,
            "granularity": granularity,
        }
        return self._get_cached_or_compute(
            operation="kpis_compare",
            params=params,
            compute=lambda: self.saas_repository.get_kpis_comparison(
                hotel_id,
                start_date,
                end_date,
                source=source,
                status=status,
                granularity=granularity,
            ),
        )

    def get_admin_audit_events(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        outcome: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return self.saas_repository.list_admin_audit_events(
            start_date=start_date,
            end_date=end_date,
            outcome=outcome,
            page=page,
            page_size=page_size,
        )

    def get_admin_audit_events_for_export(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        outcome: str | None = None,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        return self.saas_repository.list_admin_audit_events_for_export(
            start_date=start_date,
            end_date=end_date,
            outcome=outcome,
            limit=limit,
        )

    def get_admin_audit_metric_operations(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        outcome: str | None = None,
        operation: str | None = None,
        request_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return self.saas_repository.list_admin_audit_metric_operations(
            start_date=start_date,
            end_date=end_date,
            outcome=outcome,
            operation=operation,
            request_id=request_id,
            page=page,
            page_size=page_size,
        )

    def get_admin_audit_metric_operations_for_export(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        outcome: str | None = None,
        operation: str | None = None,
        request_id: str | None = None,
        limit: int = 5000,
    ) -> list[dict[str, Any]]:
        return self.saas_repository.list_admin_audit_metric_operations_for_export(
            start_date=start_date,
            end_date=end_date,
            outcome=outcome,
            operation=operation,
            request_id=request_id,
            limit=limit,
        )

    def get_admin_audit_metric_operations_metrics(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        operation: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return self.saas_repository.get_admin_audit_metric_operations_metrics(
            start_date=start_date,
            end_date=end_date,
            operation=operation,
            request_id=request_id,
        )

    def get_admin_audit_metric_operations_metrics_history(
        self,
        start_date: date,
        end_date: date,
        operation: str | None = None,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        current_day = start_date

        while current_day <= end_date:
            metrics = self.get_admin_audit_metric_operations_metrics(
                start_date=current_day,
                end_date=current_day,
                operation=operation,
                request_id=None,
            )
            items.append(
                {
                    "date": current_day.isoformat(),
                    "total_operations": int(metrics.get("total_operations", 0) or 0),
                    "replay_count": int(metrics.get("replay_count", 0) or 0),
                    "dry_run_count": int(metrics.get("dry_run_count", 0) or 0),
                    "success_count": int(metrics.get("success_count", 0) or 0),
                    "replay_ratio": float(metrics.get("replay_ratio", 0.0) or 0.0),
                    "total_processed": int(metrics.get("total_processed", 0) or 0),
                    "unique_request_ids": int(metrics.get("unique_request_ids", 0) or 0),
                }
            )
            current_day += timedelta(days=1)

        return items

    def get_admin_audit_metrics(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        return self.saas_repository.get_admin_audit_metrics(
            start_date=start_date,
            end_date=end_date,
        )

    def create_admin_audit_metrics_snapshot(
        self,
        snapshot_date: date,
        start_date: date | None = None,
        end_date: date | None = None,
        warning_threshold: float = 0.2,
        critical_threshold: float = 0.5,
        alert_status: str = "healthy",
    ) -> dict[str, Any]:
        metrics = self.get_admin_audit_metrics(start_date=start_date, end_date=end_date)
        return self.saas_repository.upsert_admin_audit_metrics_snapshot(
            snapshot_date=snapshot_date,
            metrics=metrics,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            alert_status=alert_status,
        )

    def get_admin_audit_metrics_snapshots(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        return self.saas_repository.list_admin_audit_metrics_snapshots(
            start_date=start_date,
            end_date=end_date,
        )

    def get_latest_admin_audit_metrics_snapshot(self) -> dict[str, Any] | None:
        return self.saas_repository.get_latest_admin_audit_metrics_snapshot()

    def get_admin_audit_snapshot_gaps(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        existing_dates = set(
            self.saas_repository.list_admin_audit_snapshot_dates(
                start_date=start_date,
                end_date=end_date,
            )
        )

        missing_dates: list[str] = []
        current_day = start_date
        while current_day <= end_date:
            if current_day not in existing_dates:
                missing_dates.append(current_day.isoformat())
            current_day += timedelta(days=1)

        return {
            "period": {
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
            },
            "total_days": (end_date - start_date).days + 1,
            "present_days": len(existing_dates),
            "missing_count": len(missing_dates),
            "missing_dates": missing_dates,
        }
