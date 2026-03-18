import io
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.infrastructure.persistence.sql.database import Base
from app.infrastructure.persistence.sql.models import HotelModel, UserModel
from app.interfaces.api import hotel_media as hotel_media_api
from app.interfaces.dependencies.auth import get_current_user


def _build_test_engine(tmp_path) -> tuple[object, sessionmaker]:
    db_path = tmp_path / f"hotel_media_{uuid.uuid4().hex}.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine, Session


def _seed_hotel(session, hotel_id: str) -> None:
    hotel = HotelModel(
        id=hotel_id,
        name="Hotel Teste Midia",
        address="Rua Teste, 123",
        contact_phone="5511999999999",
        checkin_time="14:00",
        checkout_time="12:00",
        cancellation_policy="policy",
        pet_policy="pet",
        child_policy="child",
        amenities="wifi",
        is_active=True,
        requires_payment_for_confirmation=False,
        allows_reservation_without_payment=True,
    )
    session.add(hotel)
    session.commit()


def _mock_user(hotel_id: str) -> UserModel:
    # Não precisa persistir; será retornado diretamente pelo override.
    return UserModel(
        id=f"user-{uuid.uuid4().hex}",
        email="user@test.com",
        password_hash="hash",
        role="admin",
        hotel_id=hotel_id,
        is_active=True,
    )


@pytest.mark.parametrize(
    "scope,room_number",
    [
        ("HOTEL", None),
        ("ROOM", "501"),
    ],
)
def test_upload_save_list_deactivate_by_scope(tmp_path, scope: str, room_number: str | None):
    hotel_id = f"hotel-{uuid.uuid4().hex}"
    _, Session = _build_test_engine(tmp_path)

    # seed
    session = Session()
    _seed_hotel(session, hotel_id=hotel_id)
    session.close()

    # override dependências/DB
    def _mock_get_current_user():
        return _mock_user(hotel_id)

    original_sessionlocal = hotel_media_api.SessionLocal
    try:
        app.dependency_overrides[get_current_user] = _mock_get_current_user
        hotel_media_api.SessionLocal = Session  # type: ignore[assignment]

        client = TestClient(app)

        file_bytes = b"fake-image-bytes"
        files = {"file": ("foto.jpg", io.BytesIO(file_bytes), "image/jpeg")}

        data = {"scope": scope}
        if scope == "ROOM":
            data["room_number"] = room_number
            assert room_number is not None

        if scope == "HOTEL":
            data["caption"] = "Foto geral"
        else:
            data["caption"] = "Foto quarto"

        resp = client.post("/saas/hotel/media", data=data, files=files)
        assert resp.status_code == 200, resp.text
        payload = resp.json()
        assert payload["success"] is True
        media_id = payload["media_id"]

        list_resp = client.get(
            "/saas/hotel/media",
            params={"scope": scope, "room_number": room_number},
        )
        assert list_resp.status_code == 200, list_resp.text
        list_payload = list_resp.json()
        assert list_payload["success"] is True

        items = list_payload["items"] or []
        assert any(i["id"] == media_id for i in items)

        # Deactivate (delete)
        del_resp = client.delete(f"/saas/hotel/media/{media_id}")
        assert del_resp.status_code == 200, del_resp.text
        assert del_resp.json()["success"] is True

        list_resp2 = client.get(
            "/saas/hotel/media",
            params={"scope": scope, "room_number": room_number},
        )
        assert list_resp2.status_code == 200, list_resp2.text
        items2 = list_resp2.json()["items"] or []
        assert not any(i["id"] == media_id for i in items2)
    finally:
        app.dependency_overrides.clear()
        hotel_media_api.SessionLocal = original_sessionlocal  # type: ignore[assignment]


def test_upload_room_requires_room_number(tmp_path):
    hotel_id = f"hotel-{uuid.uuid4().hex}"
    _, Session = _build_test_engine(tmp_path)
    session = Session()
    _seed_hotel(session, hotel_id=hotel_id)
    session.close()

    def _mock_get_current_user():
        return _mock_user(hotel_id)

    original_sessionlocal = hotel_media_api.SessionLocal
    try:
        app.dependency_overrides[get_current_user] = _mock_get_current_user
        hotel_media_api.SessionLocal = Session  # type: ignore[assignment]

        client = TestClient(app)

        files = {"file": ("foto.jpg", io.BytesIO(b"123"), "image/jpeg")}
        data = {"scope": "ROOM"}

        resp = client.post("/saas/hotel/media", data=data, files=files)
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.clear()
        hotel_media_api.SessionLocal = original_sessionlocal  # type: ignore[assignment]


def test_media_public_is_tenant_scoped(tmp_path):
    hotel_1 = f"hotel-{uuid.uuid4().hex}"
    hotel_2 = f"hotel-{uuid.uuid4().hex}"
    file_bytes = b"fake-media-public-bytes"

    _, Session = _build_test_engine(tmp_path)

    # seed
    session = Session()
    _seed_hotel(session, hotel_id=hotel_1)
    _seed_hotel(session, hotel_id=hotel_2)
    session.close()

    def _mock_get_current_user():
        return _mock_user(hotel_1)

    original_sessionlocal = hotel_media_api.SessionLocal
    try:
        app.dependency_overrides[get_current_user] = _mock_get_current_user
        hotel_media_api.SessionLocal = Session  # type: ignore[assignment]
        client = TestClient(app)

        files = {"file": ("foto.jpg", io.BytesIO(file_bytes), "image/jpeg")}
        data = {"scope": "HOTEL", "caption": "Foto geral"}

        resp = client.post("/saas/hotel/media", data=data, files=files)
        assert resp.status_code == 200, resp.text
        media_id = resp.json()["media_id"]

        ok_resp = client.get(f"/saas/hotel/{hotel_1}/media-public/{media_id}")
        assert ok_resp.status_code == 200
        assert ok_resp.content == file_bytes

        wrong_hotel_resp = client.get(f"/saas/hotel/{hotel_2}/media-public/{media_id}")
        assert wrong_hotel_resp.status_code == 404

        # rota antiga (descontinuada)
        old_resp = client.get(f"/saas/hotel/media-public/{media_id}")
        assert old_resp.status_code == 404
    finally:
        app.dependency_overrides.clear()
        hotel_media_api.SessionLocal = original_sessionlocal  # type: ignore[assignment]

