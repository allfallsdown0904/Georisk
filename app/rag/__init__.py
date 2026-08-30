"""RAG 检索增强模块：向量知识库 + 联网搜索 + 个性化风险分析智能体。

该模块设计为可复用组件：
- embeddings.py     : 文本向量化（本地哈希嵌入兜底，支持 OpenAI 兼容嵌入 API）
- vector_store.py   : 持久化向量知识库（JSON 存储 + 余弦相似度检索）
- search.py         : 联网搜索客户端抽象（Tavily 实现 + 离线兜底）
- agent.py          : 风险分析智能体（检索 -> 联网补强 -> LLM 生成个性化报告）
"""

from app.rag.agent import RiskAnalysisAgent
from app.rag.embeddings import HashEmbedder, OpenAICompatibleEmbedder, get_embedder
from app.rag.schemas import (
    Recommendation,
    RiskFact,
    RiskReport,
    Scenario,
    SearchResult,
)
from app.rag.search import DummySearchClient, TavilySearchClient, get_search_client
from app.rag.vector_store import RiskVectorStore

__all__ = [
    "HashEmbedder",
    "OpenAICompatibleEmbedder",
    "get_embedder",
    "RiskFact",
    "RiskVectorStore",
    "SearchResult",
    "DummySearchClient",
    "TavilySearchClient",
    "get_search_client",
    "Scenario",
    "Recommendation",
    "RiskReport",
    "RiskAnalysisAgent",
]
