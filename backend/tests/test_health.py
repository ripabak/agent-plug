"""Tests for the /health endpoint and its third-party checks."""


class _FakeResp:
    def __init__(self, status: int) -> None:
        self.status_code = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeClient:
    def __init__(self, status: int) -> None:
        self._status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def stream(self, method, url, **kwargs):
        return _FakeResp(self._status)


class _FakeHttpx:
    def __init__(self, status: int) -> None:
        self.AsyncClient = lambda **kwargs: _FakeClient(status)


class _FakeS3Client:
    def __init__(self, fail: bool) -> None:
        self._fail = fail

    def head_bucket(self, Bucket=None) -> None:
        if self._fail:
            raise RuntimeError("connection refused")
        return None


class _FakeS3:
    _bucket = "agent-plug"

    def __init__(self, fail: bool) -> None:
        self._client = _FakeS3Client(fail)


class _FakeEngine:
    class _Conn:
        async def __aenter__(self):
            raise RuntimeError("db unreachable")

        async def __aexit__(self, *args):
            return False

    def connect(self):
        return _FakeEngine._Conn()


def test_health_reports_all_checks(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] in ("ok", "degraded", "down")
    assert body["timestamp"]
    checks = body["checks"]
    assert set(checks) == {"database", "storage", "openrouter"}
    assert checks["database"]["status"] == "up"  # test DB is reachable
    assert checks["storage"]["backend"] == "local"
    assert checks["storage"]["status"] == "up"


def test_health_openrouter_not_configured(client, monkeypatch):
    monkeypatch.setattr("app.services.health.OPENROUTER_API_KEY", "")
    body = client.get("/health").json()
    assert body["checks"]["openrouter"]["status"] == "not_configured"
    assert body["status"] == "ok"  # not_configured is not a failure


def test_health_openrouter_up(client, monkeypatch):
    monkeypatch.setattr("app.services.health.OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setattr("app.services.health.httpx", _FakeHttpx(200))
    body = client.get("/health").json()
    assert body["checks"]["openrouter"]["status"] == "up"
    assert body["checks"]["openrouter"]["embedding_model"]


def test_health_openrouter_down_invalid_key(client, monkeypatch):
    monkeypatch.setattr("app.services.health.OPENROUTER_API_KEY", "sk-wrong")
    monkeypatch.setattr("app.services.health.httpx", _FakeHttpx(401))
    body = client.get("/health").json()
    assert body["checks"]["openrouter"]["status"] == "down"
    assert "API key" in body["checks"]["openrouter"]["error"]
    assert body["status"] == "degraded"  # DB up, dependency down


def test_health_storage_s3_up(client, monkeypatch):
    monkeypatch.setattr("app.services.health.STORAGE_BACKEND", "s3")
    monkeypatch.setattr("app.services.health.storage", _FakeS3(fail=False))
    monkeypatch.setattr("app.services.health.OPENROUTER_API_KEY", "")  # isolate
    monkeypatch.setattr("app.services.health.httpx", _FakeHttpx(200))
    body = client.get("/health").json()
    assert body["checks"]["storage"]["backend"] == "s3"
    assert body["checks"]["storage"]["status"] == "up"
    assert body["status"] == "ok"


def test_health_storage_s3_down(client, monkeypatch):
    monkeypatch.setattr("app.services.health.STORAGE_BACKEND", "s3")
    monkeypatch.setattr("app.services.health.storage", _FakeS3(fail=True))
    monkeypatch.setattr("app.services.health.OPENROUTER_API_KEY", "")  # isolate
    body = client.get("/health").json()
    assert body["checks"]["storage"]["backend"] == "s3"
    assert body["checks"]["storage"]["status"] == "down"
    assert "connection refused" in body["checks"]["storage"]["error"]
    assert body["status"] == "degraded"


def test_health_database_down(client, monkeypatch):
    monkeypatch.setattr("app.services.health.engine", _FakeEngine())
    body = client.get("/health").json()
    assert body["checks"]["database"]["status"] == "down"
    assert body["status"] == "down"  # database is critical
