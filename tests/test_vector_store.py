import json
import os

from app.rag.embeddings import HashEmbedder
from app.rag.schemas import RiskFact
from app.rag.vector_store import RiskVectorStore


def _fact(fid: str, country: str, dimension: str, text: str, score: float = 50.0) -> RiskFact:
    return RiskFact(
        id=fid,
        country=country,
        dimension=dimension,
        title=text[:20],
        text=text,
        source="测试来源",
        score=score,
        confidence=0.8,
    )


def test_add_search_and_filter():
    store = RiskVectorStore(embedder=HashEmbedder())
    store.add(_fact("kz-1", "KZ", "politics", "哈萨克斯坦大规模抗议影响项目安全"))
    store.add(_fact("kz-2", "KZ", "finance", "坚戈汇率波动推高汇兑成本"))
    store.add(_fact("ng-1", "NG", "finance", "奈拉大幅贬值引发回款风险"))

    assert len(store) == 3
    hits = store.search("哈萨克斯坦 抗议 政局", top_k=2)
    assert hits[0][0].id == "kz-1"

    hits_finance_kz = store.search("汇率", country="KZ", dimension="finance")
    assert [f.id for f, _ in hits_finance_kz] == ["kz-2"]

    hits_ng = store.search("奈拉", country="NG")
    assert [f.id for f, _ in hits_ng] == ["ng-1"]


def test_persist_round_trip(tmp_path):
    store = RiskVectorStore(embedder=HashEmbedder())
    store.add(_fact("rs-1", "RS", "policy", "塞尔维亚营商环境官僚主义与腐败"))
    path = os.path.join(tmp_path, "vector_store.json")
    store.save(path)

    loaded = RiskVectorStore(path=path)
    assert len(loaded) == 1
    fact = loaded.list_facts(country="RS")[0]
    assert fact.id == "rs-1"
    assert fact.dimension == "policy"
    assert loaded.vectors["rs-1"] == store.vectors["rs-1"]

    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    assert payload["facts"][0]["text"] == "塞尔维亚营商环境官僚主义与腐败"


def test_invalid_dimension_rejected():
    store = RiskVectorStore(embedder=HashEmbedder())
    try:
        store.add(_fact("x-1", "KZ", "unknown", "无效维度"))
        assert False, "应拒绝未知维度"
    except ValueError:
        pass


def test_remove():
    store = RiskVectorStore(embedder=HashEmbedder())
    store.add(_fact("kz-1", "KZ", "politics", "测试事实"))
    assert store.remove("kz-1") is True
    assert store.remove("kz-1") is False
    assert len(store) == 0
