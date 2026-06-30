from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Configure environment BEFORE importing the app
TMP_UPLOAD_DIR = tempfile.mkdtemp(prefix="aira_test_uploads_")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-key-please-change-in-prod"
os.environ["AI_ENABLED"] = "false"
os.environ["AUTO_SEED"] = "false"
os.environ["UPLOAD_DIR"] = TMP_UPLOAD_DIR
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["EMAIL_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app import database as database_module
from app.config import settings
from app.core.security import hash_password
from app.database import Base
from app.main import app
from app.models import Officer, Station, User, UserRole


@pytest.fixture(scope="session")
def engine():
    """Single in-memory SQLite engine shared across the session."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture(scope="session")
def TestingSessionLocal(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


@pytest.fixture(autouse=True)
def _override_db(engine, TestingSessionLocal, monkeypatch):
    """Patch app.database to use the test engine + session, then reset DB between tests."""
    monkeypatch.setattr(database_module, "engine", engine, raising=False)
    monkeypatch.setattr(database_module, "SessionLocal", TestingSessionLocal, raising=False)

    # Recreate all tables (simple fast reset for SQLite-in-memory)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Seed minimal data
    db = TestingSessionLocal()
    try:
        station = Station(
            name="Kigali Central", district="Nyarugenge", sector="Nyarugenge",
            latitude=-1.9536, longitude=30.0606, contact_phone="+250788000001",
        )
        db.add(station)
        db.flush()

        admin = User(
            full_name="Admin", email="admin@aira.example.com", password_hash=hash_password("Admin@123"),
            role=UserRole.admin, is_verified=True,
        )
        officer_user = User(
            full_name="Officer Foo", email="officer@aira.example.com",
            password_hash=hash_password("Officer@1"), role=UserRole.officer, is_verified=True,
        )
        citizen = User(
            full_name="Citizen Bar", email="citizen@aira.example.com",
            password_hash=hash_password("Citizen@1"), role=UserRole.citizen, is_verified=True,
        )
        db.add_all([admin, officer_user, citizen])
        db.flush()

        db.add(Officer(
            user_id=officer_user.id, badge_number="T-0001", station_id=station.id,
            rank="Inspector", department="Patrol",
        ))
        db.commit()
    finally:
        db.close()
    yield


@pytest.fixture
def client(TestingSessionLocal):
    def _get_db_override():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    from app.database import get_db
    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _login(client: TestClient, email: str, password: str, officer: bool = False) -> str:
    url = "/api/v1/auth/officer/login" if officer else "/api/v1/auth/login"
    r = client.post(url, json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def admin_token(client):
    return _login(client, "admin@aira.example.com", "Admin@123")


@pytest.fixture
def officer_token(client):
    return _login(client, "officer@aira.example.com", "Officer@1", officer=True)


@pytest.fixture
def citizen_token(client):
    return _login(client, "citizen@aira.example.com", "Citizen@1")


@pytest.fixture
def auth_header():
    def _hdr(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}
    return _hdr


def make_test_image_bytes(color: tuple[int, int, int] = (120, 120, 120)) -> bytes:
    """Create an in-memory JPEG of a single color for testing.

    The default is a neutral grey, which the StubAnalyzer classifies as a road
    *traffic* scene — the only incident type the app accepts (it is scoped to
    road accidents). Submission tests therefore succeed; tests that need a
    different classification pass an explicit colour (e.g. red ⇒ fire) or
    monkeypatch the analyzer.
    """
    from io import BytesIO
    from PIL import Image
    img = Image.new("RGB", (256, 256), color=color)
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()
