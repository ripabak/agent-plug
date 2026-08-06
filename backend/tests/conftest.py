"""Pytest configuration: isolated test DB, env overrides, shared fixtures.

IMPORTANT: env vars must be set BEFORE importing app modules so that
app.config picks up the test database instead of the dev one.
"""
import os

os.environ["AP_TESTING"] = "1"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:ripa@localhost:5432/agent-plug-test"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["OPENROUTER_EMBEDDING_MODEL"] = "test/embedding-model"
os.environ["OPENROUTER_BASE_URL"] = "https://example.invalid/v1"
os.environ["BACKEND_PUBLIC_URL"] = "http://localhost:8000"
os.environ["UPLOAD_DIR"] = "/tmp/agent-plug-test-uploads"

import asyncio  # noqa: E402
import shutil  # noqa: E402

import pytest  # noqa: E402

from app.config import UPLOAD_DIR  # noqa: E402
from app.database import Base, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


def _drop_all() -> None:
    async def _inner() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(_inner())


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Reset the test DB ONCE at session start (clean slate per run).

    Tables are dropped at the START (before any pytest-asyncio loops exist,
    so there are no leftover connections/locks that can stall DROP TABLE).
    """
    shutil.rmtree(UPLOAD_DIR, ignore_errors=True)  # clean uploads too
    try:
        _drop_all()
    except Exception:
        pass  # first run on a fresh DB — nothing to drop
    asyncio.run(init_db())
    yield


@pytest.fixture()
def client():
    """Sync TestClient WITHOUT lifespan (no checkpointer/rebuild side effects)."""
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture()
def auth_headers(client):
    """Register a fresh user and return auth headers."""
    email = f"user-{os.urandom(4).hex()}@example.com"
    res = client.post(
        "/api/auth/register",
        json={"email": email, "display_name": "Test User", "password": "secret123"},
    )
    assert res.status_code == 201, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email
