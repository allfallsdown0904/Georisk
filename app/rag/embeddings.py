"""文本向量化实现。

默认使用零依赖的本地哈希嵌入（对中文/英文均有效），保证离线可用；
若配置了 OpenAI 兼容的 embeddings API（如 DeepSeek / 硅基流动 / 本地服务），
则自动切换为远程嵌入以获得更好的语义质量。
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request
from typing import Protocol


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]:
        ...


class HashEmbedder:
    """字符 n-gram 哈希嵌入：确定性、零依赖、支持中英文混合文本。

    将文本切分为 2~4 字符滑动窗口，经 blake2b 哈希投影到固定维度向量并做 L2 归一化。
    语义质量弱于大模型嵌入，但作为离线兜底与演示完全够用。
    """

    def __init__(self, dim: int = 1024, n_min: int = 2, n_max: int = 4):
        self.dim = dim
        self.n_min = n_min
        self.n_max = n_max

    def _ngrams(self, text: str):
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        for n in range(self.n_min, self.n_max + 1):
            for i in range(max(0, len(normalized) - n + 1)):
                yield normalized[i : i + n]

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for gram in self._ngrams(text):
            digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(digest, "little") % self.dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec


class OpenAICompatibleEmbedder:
    """调用 OpenAI 兼容的 /embeddings 接口生成向量。

    环境变量：
    - EMBEDDING_BASE_URL : 嵌入服务地址（默认 https://api.deepseek.com/v1，可替换为任意兼容服务）
    - EMBEDDING_API_KEY  : 嵌入服务密钥
    - EMBEDDING_MODEL    : 嵌入模型名（默认 text-embedding-3-small）
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = 30,
    ):
        self.base_url = (base_url or os.getenv("EMBEDDING_BASE_URL", "https://api.deepseek.com/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("EMBEDDING_API_KEY", "")
        self.model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.timeout = timeout

    def embed(self, text: str) -> list[float]:
        if not self.api_key:
            raise RuntimeError("未配置 EMBEDDING_API_KEY，无法调用远程嵌入服务")
        payload = json.dumps({"model": self.model, "input": [text]}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/embeddings",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
            raise RuntimeError(f"远程嵌入服务调用失败: {exc}") from exc
        try:
            return [float(x) for x in data["data"][0]["embedding"]]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"远程嵌入服务返回格式异常: {data}") from exc


def get_embedder(remote: bool = True) -> Embedder:
    """工厂函数：配置了远程嵌入密钥则返回远程嵌入器，否则返回本地哈希嵌入器。"""
    if remote and os.getenv("EMBEDDING_API_KEY"):
        try:
            return OpenAICompatibleEmbedder()
        except Exception:
            pass
    return HashEmbedder()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
