"""Day27 可观测性：request_id 透传 / 替换、统一错误体。"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_request_id_roundtrip():
    r = client.get("/health", headers={"X-Request-ID": "trace-12345678"})
    assert r.headers["X-Request-ID"] == "trace-12345678"


def test_invalid_request_id_replaced():
    r = client.get("/health", headers={"X-Request-ID": 'bad id"<>'})
    assert r.headers["X-Request-ID"] != 'bad id"<>'
    assert len(r.headers["X-Request-ID"]) == 32


def test_404_unified_error():
    r = client.get("/v1/route-does-not-exist")
    body = r.json()
    assert r.status_code == 404
    assert body["error"]["code"] == "not_found"
    assert body["error"]["request_id"] == r.headers["X-Request-ID"]
