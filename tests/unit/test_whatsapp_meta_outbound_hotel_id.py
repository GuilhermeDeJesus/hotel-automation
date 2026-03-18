import importlib
import types

import pytest


class RedisClientStub:
    def __init__(self):
        self.store: dict[str, object] = {}

    def exists(self, key: str) -> int:
        return 1 if key in self.store else 0

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value, ex=None):
        self.store[key] = value

    def delete(self, key: str):
        self.store.pop(key, None)


class RedisRepoStub:
    def __init__(self):
        self.client = RedisClientStub()


class WhatsappClientStub:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []
        self.read: list[str] = []

    def send_text_message(self, to_phone: str, message: str):
        self.sent.append((to_phone, message))
        return {"success": True}

    def mark_as_read(self, message_id: str):
        self.read.append(message_id)


class UseCaseStub:
    def __init__(self):
        self.execute_calls: int = 0

    def execute(self, hotel_id: str, request_dto):
        self.execute_calls += 1
        return types.SimpleNamespace(message_type="text", reply="Olá!")


@pytest.mark.asyncio
async def test_meta_outbound_tracking_includes_hotel_id(monkeypatch):
    webhook = importlib.import_module("app.interfaces.api.whatsapp_webhook")

    whatsapp_stub = WhatsappClientStub()
    redis_stub = RedisRepoStub()
    use_case = UseCaseStub()

    track_calls: list[dict] = []

    def _track_stub(**kwargs):
        track_calls.append(kwargs)

    monkeypatch.setattr(webhook, "whatsapp_client", whatsapp_stub)
    monkeypatch.setattr(webhook, "RedisRepository", lambda: redis_stub)
    monkeypatch.setattr(webhook, "_track_saas", _track_stub)
    monkeypatch.setattr(webhook, "_acquire_redis_lock", lambda *args, **kwargs: "token")
    monkeypatch.setattr(webhook, "_release_redis_lock", lambda *args, **kwargs: None)
    monkeypatch.setattr(webhook, "_get_out_of_hours_reply_text", lambda *_: None)
    monkeypatch.setattr(webhook, "_get_whatsapp_rate_limit_debounce_seconds", lambda *_: None)

    message = {
        "id": "meta-msg-1",
        "from": "whatsapp:+5511999999999",
        "timestamp": "123",
        "type": "text",
        "text": {"body": "Oi"},
    }

    resp = await webhook._handle_incoming_message(
        message=message,
        use_case=use_case,
        hotel_id="hotel-1",
        public_media_base_url="http://test.local",
    )

    assert resp.status_code == 200
    assert use_case.execute_calls == 1

    outbound_calls = [c for c in track_calls if c.get("event_type") == "outbound_message"]
    assert outbound_calls
    assert all(call.get("hotel_id") == "hotel-1" for call in outbound_calls)


@pytest.mark.asyncio
async def test_meta_webhook_ignores_when_hotel_id_none(monkeypatch):
    webhook = importlib.import_module("app.interfaces.api.whatsapp_webhook")

    whatsapp_stub = WhatsappClientStub()
    redis_stub = RedisRepoStub()
    use_case = UseCaseStub()
    track_calls: list[dict] = []

    def _track_stub(**kwargs):
        track_calls.append(kwargs)

    monkeypatch.setattr(webhook, "whatsapp_client", whatsapp_stub)
    monkeypatch.setattr(webhook, "RedisRepository", lambda: redis_stub)
    monkeypatch.setattr(webhook, "_track_saas", _track_stub)
    monkeypatch.setattr(webhook, "_get_out_of_hours_reply_text", lambda *_: None)
    monkeypatch.setattr(webhook, "_get_whatsapp_rate_limit_debounce_seconds", lambda *_: None)
    monkeypatch.setattr(webhook, "_acquire_redis_lock", lambda *args, **kwargs: "token")
    monkeypatch.setattr(webhook, "_release_redis_lock", lambda *args, **kwargs: None)

    message = {
        "id": "meta-msg-2",
        "from": "whatsapp:+5511888777666",
        "timestamp": "123",
        "type": "text",
        "text": {"body": "Oi"},
    }

    resp = await webhook._handle_incoming_message(
        message=message,
        use_case=use_case,
        hotel_id=None,
        public_media_base_url="http://test.local",
    )

    assert resp.status_code == 200
    assert use_case.execute_calls == 0
    assert not track_calls

