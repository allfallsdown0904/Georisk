"""GDELT 搜索客户端测试：解析格式 + 提供方选择逻辑。"""

import json
from unittest.mock import MagicMock, patch

from app.rag.search import BingNewsSearchClient, DummySearchClient, GDELTSearchClient, TavilySearchClient, get_search_client


def test_gdelt_parses_articles(monkeypatch):
    client = GDELTSearchClient(timespan="1y")

    def fake_urlopen(req, timeout=30):
        class FakeResp:
            def read(self):
                return json.dumps(
                    {
                        "articles": [
                            {
                                "title": "Serbia protests continue",
                                "url": "https://news.example.com/a",
                                "domain": "news.example.com",
                                "seendate": "20251201080000",
                                "language": "English",
                            },
                            {
                                "title": "塞尔维亚抗议持续",
                                "url": "https://zh.example.com/b",
                                "domain": "zh.example.com",
                                "seendate": "20251202",
                                "language": "Chinese",
                            },
                        ]
                    }
                ).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return FakeResp()

    mock_urlopen = MagicMock(side_effect=fake_urlopen)
    with patch("app.rag.search.urllib.request.urlopen", mock_urlopen):
        results = client.search("塞尔维亚 抗议", max_results=5)

    assert len(results) == 2
    assert results[0].title == "Serbia protests continue"
    assert results[0].date == "2025-12-01"
    assert results[0].source == "news.example.com"
    assert results[1].date == "2025-12-02"
    # 请求参数应包含查询与时间窗
    called_url = mock_urlopen.call_args[0][0].full_url
    assert "query=" in called_url and "timespan=1y" in called_url


def test_get_search_client_provider_selection(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("SEARCH_PROVIDER", "gdelt")
    assert isinstance(get_search_client(), GDELTSearchClient)

    monkeypatch.setenv("SEARCH_PROVIDER", "none")
    assert isinstance(get_search_client(), DummySearchClient)

    monkeypatch.setenv("SEARCH_PROVIDER", "auto")
    assert isinstance(get_search_client(), BingNewsSearchClient), "auto 且无 Key 时应使用 Bing News 兜底"

    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setenv("SEARCH_PROVIDER", "auto")
    assert isinstance(get_search_client(), TavilySearchClient), "auto 且配置 Key 时应优先 Tavily"

    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("SEARCH_PROVIDER", "tavily")
    assert isinstance(get_search_client(), DummySearchClient), "显式 tavily 但无 Key 时应离线兜底"


