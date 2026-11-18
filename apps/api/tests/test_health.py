from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["env"] in {"dev", "test", "prod"}


def test_health_uses_injected_settings():
    # 不读 .env，直接注入 —— 明天用同样手法注入假 LLM provider
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, app_env="test")
    try:
        r = client.get("/health")
    finally:
        app.dependency_overrides.clear()
    assert r.json()["env"] == "test"
