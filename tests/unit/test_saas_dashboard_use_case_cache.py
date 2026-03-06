from __future__ import annotations

from app.application.use_cases.get_saas_dashboard import GetSaaSDashboardUseCase


class InMemoryCache:
    def __init__(self):
        self.store = {}

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value, ttl_seconds: int = 3600):
        self.store[key] = value

    def delete(self, key: str):
        self.store.pop(key, None)

    def exists(self, key: str) -> bool:
        return key in self.store

    def clear(self):
        self.store.clear()


class FakeRedisClient:
    def __init__(self, cache: InMemoryCache):
        self.cache = cache

    def scan_iter(self, match: str):
        prefix = match.replace("*", "")
        for key in list(self.cache.store.keys()):
            if key.startswith(prefix):
                yield key


class InMemoryCacheWithClient(InMemoryCache):
    def __init__(self):
        super().__init__()
        self.client = FakeRedisClient(self)


class FakeSaaSRepository:
    def __init__(self):
        self.kpis_calls = 0

    def get_kpis(self, *args, **kwargs):
        self.kpis_calls += 1
        return {"ok": True, "calls": self.kpis_calls}

    def list_leads(self, *args, **kwargs):
        return []

    def get_funnel(self, *args, **kwargs):
        return {"stages": [], "total": 0}

    def get_timeseries(self, *args, **kwargs):
        return {"points": []}

    def get_kpis_comparison(self, *args, **kwargs):
        return {"current": {}, "previous": {}, "delta": {}}


def test_get_kpis_uses_cache_after_first_call():
    repo = FakeSaaSRepository()
    cache = InMemoryCache()
    use_case = GetSaaSDashboardUseCase(
        saas_repository=repo,
        cache_repository=cache,
        cache_ttl_seconds=120,
    )

    first = use_case.get_kpis(None, None, source="twilio", status="ENGAGED", granularity="week")
    second = use_case.get_kpis(None, None, source="twilio", status="ENGAGED", granularity="week")

    assert first["ok"] is True
    assert second["ok"] is True
    assert repo.kpis_calls == 1


def test_invalidate_analytics_cache_removes_only_dashboard_keys():
    cache = InMemoryCacheWithClient()
    cache.set("saas:dashboard:kpis:abc", {"x": 1})
    cache.set("saas:dashboard:timeseries:def", {"x": 2})
    cache.set("conversation:5511", [{"role": "user", "content": "oi"}])

    deleted = GetSaaSDashboardUseCase.invalidate_analytics_cache(cache)

    assert deleted == 2
    assert cache.get("saas:dashboard:kpis:abc") is None
    assert cache.get("saas:dashboard:timeseries:def") is None
    assert cache.get("conversation:5511") is not None
