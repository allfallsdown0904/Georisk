"""Bing 新闻 RSS 客户端测试：XML 解析与日期转换。"""

from unittest.mock import MagicMock, patch

from app.rag.search import BingNewsSearchClient


RSS_XML = """<?xml version="1.0" encoding="utf-8" ?>
<rss version="2.0"><channel><title>Bing News</title>
<item>
  <title>塞尔维亚政局动态：大规模抗议仍在持续</title>
  <link>http://www.bing.com/news/apiclick.aspx?ref=FexRss&amp;tid=1</link>
  <pubDate>Fri, 14 Nov 2025 09:46:00 GMT</pubDate>
  <description>&lt;p&gt;塞尔维亚近期政治局势备受关注&lt;/p&gt;</description>
</item>
<item>
  <title>Kazakhstan tax reform investors</title>
  <link>http://www.bing.com/news/apiclick.aspx?ref=FexRss&amp;tid=2</link>
  <pubDate>Sat, 22 Aug 2026 05:03:00 GMT</pubDate>
  <description>Economic resilience and investment outlook.</description>
</item>
</channel></rss>"""


def test_bing_parses_rss(monkeypatch):
    client = BingNewsSearchClient()

    def fake_urlopen(req, timeout=20):
        class FakeResp:
            def read(self):
                return RSS_XML.encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return FakeResp()

    mock_urlopen = MagicMock(side_effect=fake_urlopen)
    with patch("app.rag.search.urllib.request.urlopen", mock_urlopen):
        results = client.search("塞尔维亚 政局", max_results=5)

    assert len(results) == 2
    assert results[0].title == "塞尔维亚政局动态：大规模抗议仍在持续"
    assert results[0].date == "2025-11-14"
    assert results[0].source == "Bing News"
    assert "政治局势" in results[0].snippet  # 已去除 HTML 标签
    assert results[1].date == "2026-08-22"
    called_url = mock_urlopen.call_args[0][0].full_url
    assert "format=rss" in called_url and "q=" in called_url
