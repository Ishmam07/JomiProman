"""Test setup: temp SQLite DB, no Redis, no Groq key, fresh demo data per test."""

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="jomiproman-tests-"))
os.environ.update(
    DATABASE_URL=f"sqlite:///{_TMP / 'test.db'}",
    REDIS_URL="",
    SIGNING_KEY_B64="",
    SIGNING_KEY_PATH=str(_TMP / "ed25519.key"),
    GROQ_API_KEY="",
    AUTO_SEED="false",
    REGISTRAR_KEY="test-key",
    ADMIN_KEY="test-admin-key",
    ENVIRONMENT="development",
    RATE_LIMIT_PER_MINUTE="30",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.deps import get_cache, get_signer  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_demo  # noqa: E402

AUTH = {"X-Registrar-Key": "test-key"}


@pytest.fixture()
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    get_cache().clear_memory()
    with SessionLocal() as session:
        seed_demo(session, get_signer())
        yield session


@pytest.fixture()
def client(db):
    with TestClient(app) as c:
        yield c


def deed_body(**overrides):
    body = {
        "mouza": "রহিমপুর",
        "dag": 412,
        "seller": "করিম",
        "buyer": "রফিক",
        "area": 6,
        "deed_date": "2026-10-17",
    }
    body.update(overrides)
    return body


def register(client, **overrides):
    return client.post("/api/deeds", json=deed_body(**overrides), headers=AUTH)


def codes(payload):
    return {f["code"] for f in payload["findings"]}
