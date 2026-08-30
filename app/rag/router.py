"""FastAPI 路由：将 RAG 智能体暴露为 HTTP API。

在 app/main.py 中 include 本路由即可（见 docs/vector_db_design.md）：
    from app.rag.router import router as rag_router
    app.include_router(rag_router)
"""

from __future__ import annotations

import os

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.rag.agent import RiskAnalysisAgent, default_llm_call
from app.rag.search import get_search_client
from app.rag.vector_store import RiskVectorStore

router = APIRouter(prefix="/api/rag", tags=["rag"])

# 模块级单例：首次使用时加载向量库（构建产物 data/vector_store.json）
_store: RiskVectorStore | None = None
_agent: RiskAnalysisAgent | None = None


def _get_agent() -> RiskAnalysisAgent:
    global _store, _agent
    if _agent is None:
        if not os.path.exists("data/vector_store.json"):
            raise RuntimeError("向量库不存在，请先运行: python scripts/build_vector_db.py")
        try:
            _store = RiskVectorStore(path="data/vector_store.json")
        except FileNotFoundError as exc:
            raise RuntimeError(
                "向量库不存在，请先运行: python scripts/build_vector_db.py"
            ) from exc
        _agent = RiskAnalysisAgent(
            vector_store=_store,
            search_client=get_search_client(),
            llm_call=default_llm_call,
        )
    return _agent


class AnalyzeRequest(BaseModel):
    country: str = Field(..., description="国家代码（ISO3），如 KZ / NG / RS")
    project: str = Field("", description="项目/业务背景，用于个性化建议")
    question: str = Field("", description="用户问题")
    top_k: int = Field(10, ge=1, le=50)
    web_queries: list[str] | None = Field(None, description="自定义联网搜索词（可选）")
    max_web_results: int = Field(5, ge=1, le=10)


@router.get("/health")
def health() -> dict:
    store = _get_agent().store
    return {
        "status": "ok",
        "facts": len(store),
        "countries": store.list_countries(),
        "embedder": type(store.embedder).__name__,
    }


@router.get("/countries")
def countries() -> dict:
    return {"countries": _get_agent().store.list_countries()}


@router.post("/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    try:
        agent = _get_agent()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    try:
        report = agent.analyze(
            country=req.country,
            project=req.project,
            question=req.question,
            top_k=req.top_k,
            web_queries=req.web_queries,
            max_web_results=req.max_web_results,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"分析失败: {exc}") from exc
    return report.to_dict()


@router.get("/facts")
def facts(
    country: str | None = Query(None, description="国家代码"),
    dimension: Literal["politics", "finance", "policy", "society", "exit"] | None = Query(None),
) -> dict:
    store = _get_agent().store
    items = [
        f.to_dict()
        for f in store.list_facts(country=country)
        if dimension is None or f.dimension == dimension
    ]
    return {"count": len(items), "facts": items}
