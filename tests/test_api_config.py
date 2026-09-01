from fastapi.testclient import TestClient

from app import config
from app.main import app

client = TestClient(app)


def test_import_api_key_saves_private_txt_and_uses_it(monkeypatch, tmp_path):
    key_file = tmp_path / "runtime" / "api_key.txt"
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(config, "API_KEY_FILE", key_file)
    monkeypatch.setattr(config, "_runtime_api_key", None)

    res = client.post("/api/config/api-key", json={"api_key": "  test-secret-key  "})

    assert res.status_code == 200
    assert res.json()["configured"] is True
    assert "test-secret-key" not in res.text
    assert key_file.read_text(encoding="utf-8") == "test-secret-key"
    assert key_file.stat().st_mode & 0o777 == 0o600
    assert config.get_api_key() == "test-secret-key"


def test_import_api_key_rejects_whitespace(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "API_KEY_FILE", tmp_path / "runtime" / "api_key.txt")
    monkeypatch.setattr(config, "_runtime_api_key", None)

    res = client.post("/api/config/api-key", json={"api_key": "bad key"})

    assert res.status_code == 400
    assert not config.API_KEY_FILE.exists()


def test_import_api_key_rejects_remote_client():
    remote_client = TestClient(app, client=("203.0.113.10", 50000))

    res = remote_client.post("/api/config/api-key", json={"api_key": "test-secret-key"})

    assert res.status_code == 403
