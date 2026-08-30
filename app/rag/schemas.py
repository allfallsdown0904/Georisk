"""RAG 模块的数据结构定义（纯 dataclass，不依赖外部框架，便于复用）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# 风险维度统一标识（与 data/risk_indicators.csv 保持一致）
DIMENSIONS = {
    "politics": "政局与地缘冲突",
    "finance": "金融与外汇",
    "policy": "政策与法规",
    "society": "社会与安全秩序",
    "exit": "退出与沉没成本",
}


@dataclass
class RiskFact:
    """知识库中的一条风险事实。"""

    id: str
    country: str
    dimension: str
    title: str
    text: str
    source: str
    source_url: str = ""
    date: str = ""
    score: float = 50.0  # 0-100，该事实对风险的贡献度
    confidence: float = 0.5  # 0-1，信源可信度
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "country": self.country,
            "dimension": self.dimension,
            "title": self.title,
            "text": self.text,
            "source": self.source,
            "source_url": self.source_url,
            "date": self.date,
            "score": self.score,
            "confidence": self.confidence,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RiskFact":
        return cls(**data)


@dataclass
class SearchResult:
    """联网搜索返回的一条标准化结果。"""

    title: str
    url: str
    snippet: str
    date: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "date": self.date,
            "source": self.source,
        }


@dataclass
class Scenario:
    """情景推演：乐观 / 基准 / 压力。"""

    name: str  # 乐观情景 / 基准情景 / 压力情景
    summary: str
    triggers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "summary": self.summary, "triggers": list(self.triggers)}


@dataclass
class Recommendation:
    """一条个性化建议。"""

    action: str
    priority: str = "中"  # 高 / 中 / 低
    timeframe: str = ""
    cost_estimate: str = ""
    evidence: list[str] = field(default_factory=list)  # 事实 id / [web:n] 引用
    confidence: float = 0.5
    needs_human_review: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "priority": self.priority,
            "timeframe": self.timeframe,
            "cost_estimate": self.cost_estimate,
            "evidence": list(self.evidence),
            "confidence": self.confidence,
            "needs_human_review": self.needs_human_review,
        }


@dataclass
class RiskReport:
    """智能体输出的完整风险分析报告。"""

    country: str
    project: str
    generated_at: str
    overall_risk: str  # 低 / 中 / 高
    overall_score: float
    dimensions: dict[str, dict[str, Any]] = field(default_factory=dict)
    key_risks: list[dict[str, Any]] = field(default_factory=list)
    scenarios: list[Scenario] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    watchlist: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    llm_unavailable: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "country": self.country,
            "project": self.project,
            "generated_at": self.generated_at,
            "overall_risk": self.overall_risk,
            "overall_score": self.overall_score,
            "dimensions": self.dimensions,
            "key_risks": self.key_risks,
            "scenarios": [s.to_dict() for s in self.scenarios],
            "recommendations": [r.to_dict() for r in self.recommendations],
            "watchlist": self.watchlist,
            "sources": self.sources,
            "llm_unavailable": self.llm_unavailable,
            "notes": self.notes,
        }


def risk_level(score: float) -> str:
    """将 0-100 分数映射为风险等级：低(<40) / 中(<70) / 高(>=70)。"""
    if score < 40:
        return "低"
    if score < 70:
        return "中"
    return "高"
