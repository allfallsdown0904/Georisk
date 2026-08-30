"""联网搜索客户端抽象。

通过统一接口向外部搜索 API 发起查询并返回标准化结果。
默认实现 Tavily Search API（需 TAVILY_API_KEY）；未配置密钥时自动退化为
离线模式（返回空结果），保证系统在无网络/无密钥时仍可运行。
"""

from __future__ import annotations

import json
import os
import urllib.error
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


class DummySearchClient:
    """离线兜底：不发起任何请求，返回空结果。"""

    def search(self, query: str, max_results: int = 8) -> list[SearchResult]:
        return []


def get_search_client() -> SearchClient:
    """工厂函数：按环境变量 SEARCH_PROVIDER（tavily / none）创建搜索客户端。"""
    provider = os.getenv("SEARCH_PROVIDER", "tavily").strip().lower()
    if provider == "none":
        return DummySearchClient()
    if provider == "tavily":
        if os.getenv("TAVILY_API_KEY"):
            return TavilySearchClient()
        return DummySearchClient()
    raise ValueError(f"未知 SEARCH_PROVIDER: {provider}，可选 tavily / none")
