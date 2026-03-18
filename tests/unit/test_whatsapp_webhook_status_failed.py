import importlib
import os


def test_handle_message_status_failed_notifies_user(monkeypatch):
    # Importar o módulo exige DATABASE_URL configurado (setup de SQLAlchemy).
    # Para unit test, usamos SQLite em memória.
    monkeypatch.setenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    os.environ["TEST_DATABASE_URL"] = "sqlite:///:memory:"

    webhook = importlib.import_module("app.interfaces.api.whatsapp_webhook")

    class RedisClientStub:
        def __init__(self):
            self._store = {}

        def exists(self, key):
            return 1 if key in self._store else 0

        def set(self, key, value, ex=None):
            self._store[key] = value

    class RedisRepoStub:
        def __init__(self):
            self.client = RedisClientStub()

    class WhatsappClientStub:
        def __init__(self):
            self.sent = []

        def send_text_message(self, to_phone, message):
            self.sent.append((to_phone, message))
            return {"success": True}

    redis_stub = RedisRepoStub()
    whatsapp_stub = WhatsappClientStub()

    # Patch global clients + RedisRepository constructor
    monkeypatch.setattr(webhook, "whatsapp_client", whatsapp_stub)
    monkeypatch.setattr(webhook, "RedisRepository", lambda: redis_stub)

    status = {
        "id": "status-1",
        "status": "failed",
        "recipient_id": "5561999999999",
        "timestamp": "123",
    }

    webhook._handle_message_status(status, hotel_id="hotel-1")

    assert len(whatsapp_stub.sent) == 1
    to_phone, message = whatsapp_stub.sent[0]
    assert to_phone == "5561999999999"
    assert "não consegui enviar" in message.lower()

