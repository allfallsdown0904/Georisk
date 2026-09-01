from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_analyze_requires_key(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.config, "get_api_key", lambda: "")
    res = client.post("/api/analyze", json={"country_code": "KZ", "project_type": "EPC工程总承包"})
    assert res.status_code == 503
    assert "API Key" in res.json()["detail"]


def test_analyze_with_mocked_llm(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.config, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(main, "analyze_country", lambda c, p, s: f"模拟分析：{c} / {p}")

    res = client.post("/api/analyze", json={"country_code": "KZ", "project_type": "EPC工程总承包"})
    assert res.status_code == 200
    body = res.json()
    assert body["country_code"] == "KZ"
    assert body["project_type"] == "EPC工程总承包"
    assert body["analysis"].startswith("模拟分析")


def test_analyze_unknown_country(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.config, "get_api_key", lambda: "test-key")
    res = client.post("/api/analyze", json={"country_code": "XX", "project_type": "EPC工程总承包"})
    assert res.status_code == 404
