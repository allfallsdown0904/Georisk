"""持久化向量知识库。

以 JSON 文件保存事实与向量，支持按国家/维度过滤的余弦相似度检索。
无外部数据库依赖，便于嵌入任何 Python 项目；数据量增大后可无缝替换为
ChromaDB / FAISS / Milvus（仅需实现相同接口）。
"""

from __future__ import annotations

import json
import os
from typing import Iterable

from app.rag.embeddings import Embedder, cosine_similarity, get_embedder
from app.rag.schemas import DIMENSIONS, RiskFact


class RiskVectorStore:
    def __init__(self, embedder: Embedder | None = None, path: str | None = None):
        self.embedder = embedder or get_embedder()
        self.path = path
        self.facts: dict[str, RiskFact] = {}
        self.vectors: dict[str, list[float]] = {}
        if path and os.path.exists(path):
            self.load(path)

    # ---------- 写入 ----------
    def add(self, fact: RiskFact) -> None:
        if fact.dimension not in DIMENSIONS:
            raise ValueError(f"未知风险维度: {fact.dimension}，可选 {list(DIMENSIONS)}")
        self.facts[fact.id] = fact
        self.vectors[fact.id] = self.embedder.embed(f"{fact.title}。{fact.text}。{fact.country} {DIMENSIONS[fact.dimension]} {' '.join(fact.tags)}")

    def add_many(self, facts: Iterable[RiskFact]) -> int:
        count = 0
        for fact in facts:
            self.add(fact)
            count += 1
        return count

    def remove(self, fact_id: str) -> bool:
        removed = self.facts.pop(fact_id, None) is not None
        self.vectors.pop(fact_id, None)
        return removed

    # ---------- 检索 ----------
    def search(
        self,
        query: str,
        top_k: int = 8,
        country: str | None = None,
        dimension: str | None = None,
        min_score: float = 0.0,
    ) -> list[tuple[RiskFact, float]]:
        """返回 (事实, 相似度) 列表，按相似度降序。"""
        query_vec = self.embedder.embed(query)
        scored: list[tuple[RiskFact, float]] = []
        for fact_id, fact in self.facts.items():
            if country and fact.country.upper() != country.upper():
                continue
            if dimension and fact.dimension != dimension:
                continue
            sim = cosine_similarity(query_vec, self.vectors[fact_id])
            if sim < min_score:
                continue
            scored.append((fact, sim))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]

    # ---------- 持久化 ----------
    def save(self, path: str | None = None) -> str:
        target = path or self.path
        if not target:
            raise ValueError("未指定保存路径")
        payload = {
            "facts": [f.to_dict() for f in self.facts.values()],
            "vectors": self.vectors,
        }
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        self.path = target
        return target

    def load(self, path: str) -> "RiskVectorStore":
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        self.facts = {f["id"]: RiskFact.from_dict(f) for f in payload.get("facts", [])}
        self.vectors = {k: [float(x) for x in v] for k, v in payload.get("vectors", {}).items()}
        self.path = path
        return self

    # ---------- 统计与工具 ----------
    def __len__(self) -> int:
        return len(self.facts)

    def list_countries(self) -> list[str]:
        return sorted({f.country for f in self.facts.values()})

    def list_facts(self, country: str | None = None) -> list[RiskFact]:
        facts = list(self.facts.values())
        if country:
            facts = [f for f in facts if f.country.upper() == country.upper()]
        return sorted(facts, key=lambda f: (f.country, f.dimension, f.id))

    @classmethod
    def build_from_seed(
        cls,
        seed_dir: str,
        embedder: Embedder | None = None,
        save_path: str | None = None,
    ) -> "RiskVectorStore":
        """从 data/seed/*.json 批量构建知识库并（可选）持久化。"""
        store = cls(embedder=embedder)
        for filename in sorted(os.listdir(seed_dir)):
            if not filename.endswith(".json"):
                continue
            with open(os.path.join(seed_dir, filename), "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            facts = [RiskFact.from_dict(item) for item in payload.get("facts", [])]
            store.add_many(facts)
        if save_path:
            store.save(save_path)
        return store
