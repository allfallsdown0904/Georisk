"""联网搜索客户端抽象。

通过统一接口向外部搜索 API 发起查询并返回标准化结果。
默认实现 Tavily Search API（需 TAVILY_API_KEY）；未配置密钥时自动退化为
离线模式（返回空结果），保证系统在无网络/无密钥时仍可运行。
"""

from __future__ import annotations

import email.utils
import json
import os
import re
import xml.etree.ElementTree as ET
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Protocol

from app.rag.schemas import SearchResult


class SearchClient(Protocol):
    def search(self, query: str, max_results: int = 8) -> list[SearchResult]:
        ...


class TavilySearchClient:
    """Tavily Search API 客户端（https://tavily.com）。

    环境变量：TAVILY_API_KEY
    """

    ENDPOINT = "https://api.tavily.com/search"

    def __init__(self, api_key: str | None = None, timeout: int = 30, endpoint: str | None = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        self.timeout = timeout
        self.endpoint = endpoint or self.ENDPOINT
        if not self.api_key:
            raise RuntimeError("未配置 TAVILY_API_KEY")

    def search(self, query: str, max_results: int = 8) -> list[SearchResult]:
        payload = json.dumps(
            {
                "api_key": self.api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
                "include_answer": False,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Tavily 搜索调用失败: {exc}") from exc

        results: list[SearchResult] = []
        for item in data.get("results", []):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    date=item.get("published_date", "") or "",
                    source=item.get("source", ""),
                )
            )
        return results


class BingNewsSearchClient:
    """Bing 新闻 RSS 客户端（https://www.bing.com/news/search?q=...&format=rss）。

    免密钥、国内可达，作为联网搜索的稳定兜底；结果数较少但可作为信号补充。
    """

    ENDPOINT = "https://www.bing.com/news/search"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    @staticmethod
    def _strip_html(text: str) -> str:
        return re.sub(r"<[^>]+>", "", text).replace("&amp;", "&").strip()

    def search(self, query: str, max_results: int = 8) -> list[SearchResult]:
        params = urllib.parse.urlencode({"q": query, "format": "rss"})
        req = urllib.request.Request(
            f"{self.ENDPOINT}?{params}",
            headers={"User-Agent": self.USER_AGENT},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"Bing News 搜索调用失败: {exc}") from exc
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise RuntimeError(f"Bing News 返回格式异常: {exc}") from exc
        results: list[SearchResult] = []
        for item in root.findall(".//item")[:max_results]:
            title = self._strip_html(item.findtext("title", "") or "")
            desc = self._strip_html(item.findtext("description", "") or "")
            pub = item.findtext("pubDate", "") or ""
            date = ""
            try:
                date = email.utils.parsedate_to_datetime(pub).date().isoformat()
            except Exception:
                date = pub[:16]
            results.append(
                SearchResult(
                    title=title,
                    url=item.findtext("link", "") or "",
                    snippet=desc or title,
                    date=date,
                    source="Bing News",
                )
            )
        return results

class GDELTSearchClient:
    """GDELT DOC 2.0 API 客户端（https://www.gdeltproject.org）。

    免密钥、覆盖全球新闻与事件（每 15 分钟更新），特别适合国别风险信号检索；
    查询词会自动跨语言匹配（含中文）。环境变量 GDELT_TIMESPAN 可调时间窗（默认 2y）。
    """

    ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"

    def __init__(self, timeout: int = 60, timespan: str | None = None, retries: int = 2):
        self.timeout = timeout
        self.timespan = timespan or os.getenv("GDELT_TIMESPAN", "2y")
        self.retries = retries

    def search(self, query: str, max_results: int = 8) -> list[SearchResult]:
        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": str(max_results),
            "timespan": self.timespan,
        }
        req = urllib.request.Request(
            f"{self.ENDPOINT}?{urllib.parse.urlencode(params)}",
            headers={"User-Agent": "Georisk/1.0"},
            method="GET",
        )
        data = None
        last_exc: Exception | None = None
        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_exc = exc
                if attempt < self.retries - 1:
                    time.sleep(2)
        if data is None:
            raise RuntimeError(f"GDELT 搜索调用失败（已重试 {self.retries} 次）: {last_exc}")
        results: list[SearchResult] = []
        for item in data.get("articles", []):
            title = item.get("title", "") or ""
            date_raw = item.get("seendate", "") or ""
            date = date_raw[:8] if len(date_raw) >= 8 else ""
            if len(date) == 8:
                date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
            results.append(
                SearchResult(
                    title=title,
                    url=item.get("url", "") or "",
                    snippet=f"{title}（{item.get('domain', '') or '来源未知'}）",
                    date=date,
                    source=item.get("domain", "") or "GDELT",
                )
            )
        return results

class DummySearchClient:
    """离线兜底：不发起任何请求，返回空结果。"""

    def search(self, query: str, max_results: int = 8) -> list[SearchResult]:
        return []


def get_search_client() -> SearchClient:
    """工厂函数：按环境变量 SEARCH_PROVIDER（auto / tavily / gdelt / none）创建搜索客户端。"""
    provider = os.getenv("SEARCH_PROVIDER", "auto").strip().lower()
    if provider == "none":
        return DummySearchClient()
    if provider == "auto":
        # 优先 Tavily（更及时的新闻检索）；未配置 Key 时自动降级到免密钥的 GDELT
        if os.getenv("TAVILY_API_KEY"):
            return TavilySearchClient()
        return BingNewsSearchClient()
    if provider == "tavily":
        if os.getenv("TAVILY_API_KEY"):
            return TavilySearchClient()
        return DummySearchClient()
    if provider == "gdelt":
        return GDELTSearchClient()
    if provider == "bing":
        return BingNewsSearchClient()
    raise ValueError(f"未知 SEARCH_PROVIDER: {provider}，可选 auto / tavily / gdelt / bing / none")
