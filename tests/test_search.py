import json
from unittest.mock import patch

from app.rag.search import DummySearchClient, TavilySearchClient


def test_dummy_search_client_returns_empty():
    client = DummySearchClient()
    assert client.search("任何查询") == []


def test_tavily_search_client_parses_results(monkeypatch):
    client = TavilySearchClient(api_key="test-key")

    def fake_urlopen(req, timeout=30):
        class FakeResp:
            def read(self):
                return json.dumps(
                    {
                        "results": [
                            {
                                "title": "测试标题",
                                "url": "https://example.com/a",
                                "content": "摘要内容",
                                "published_date": "2025-10-01",
                                "source": "示例源",
                            }
                        ]
                    }
                ).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return FakeResp()

    with patch("app.rag.search.urllib.request.urlopen", fake_urlopen):
        results = client.search("塞尔维亚风险", max_results=5)
    assert len(results) == 1
    assert results[0].title == "测试标题"
    assert results[0].url == "https://example.com/a"
    assert results[0].date == "2025-10-01"


def test_tavily_requires_api_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    try:
        TavilySearchClient(api_key="")
        assert False, "缺少 API Key 时应报错"
    except RuntimeError:
        pass
