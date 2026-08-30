import json

from app.rag.agent import RiskAnalysisAgent, _extract_json
from app.rag.embeddings import HashEmbedder
from app.rag.schemas import RiskFact
from app.rag.search import DummySearchClient
from app.rag.vector_store import RiskVectorStore


def _build_store() -> RiskVectorStore:
    store = RiskVectorStore(embedder=HashEmbedder())
    facts = [
        RiskFact(
            id="kz-1", country="KZ", dimension="politics", title="哈政治稳定",
            text="哈萨克斯坦政局总体稳定但受大国博弈影响", source="测试源", score=60, confidence=0.8,
        ),
        RiskFact(
            id="kz-2", country="KZ", dimension="finance", title="汇率风险",
            text="坚戈存在贬值压力，高利率推高融资成本", source="测试源", score=65, confidence=0.8,
        ),
    ]
    store.add_many(facts)
    return store


def test_rule_based_fallback_report():
    store = _build_store()
    agent = RiskAnalysisAgent(vector_store=store, search_client=DummySearchClient())
    report = agent.analyze(country="KZ", project="矿山设备供应", question="当前主要风险是什么？")

    assert report.country == "哈萨克斯坦"
    assert report.overall_risk in ("低", "中", "高")
    assert 0 <= report.overall_score <= 100
    assert set(report.dimensions) == {"politics", "finance", "policy", "society", "exit"}
    assert report.key_risks
    assert len(report.scenarios) == 3
    assert {s.name for s in report.scenarios} == {"乐观情景", "基准情景", "压力情景"}
    assert report.recommendations
    assert report.sources
    assert report.llm_unavailable is True
    assert any("LLM" in n for n in report.notes)


def test_llm_synthesis_path():
    store = _build_store()
    expected = {
        "overall_risk": "中",
        "overall_score": 62,
        "dimensions": {
            "politics": {"score": 60, "summary": "政局稳定但受博弈影响"},
            "finance": {"score": 65, "summary": "汇率与利率风险"},
            "policy": {"score": 50, "summary": ""},
            "society": {"score": 50, "summary": ""},
            "exit": {"score": 50, "summary": ""},
        },
        "key_risks": [
            {
                "risk": "汇率波动",
                "impact": "回款缩水",
                "likelihood": "中",
                "evidence": ["kz-2"],
                "confidence": 0.8,
                "needs_human_review": True,
            }
        ],
        "scenarios": [
            {"name": "乐观情景", "summary": "汇率企稳", "triggers": ["油价稳定"]},
            {"name": "基准情景", "summary": "风险可控", "triggers": []},
            {"name": "压力情景", "summary": "汇率大幅贬值", "triggers": ["大宗商品下跌"]},
        ],
        "recommendations": [
            {
                "action": "建立汇率套保",
                "priority": "高",
                "timeframe": "1 个月内",
                "cost_estimate": "约 1%-3%",
                "evidence": ["kz-2"],
                "confidence": 0.8,
                "needs_human_review": True,
            }
        ],
        "watchlist": ["NBS 利率决议", "油价"],
    }

    def fake_llm(system, user):
        assert "kz-2" in user and "哈萨克斯坦" in user
        return json.dumps(expected, ensure_ascii=False)

    agent = RiskAnalysisAgent(vector_store=store, search_client=DummySearchClient(), llm_call=fake_llm)
    report = agent.analyze(country="KZ", project="矿山设备")

    assert report.llm_unavailable is False
    assert report.overall_risk == "中"
    assert report.dimensions["finance"]["score"] == 65
    assert report.recommendations[0].evidence == ["kz-2"]
    assert report.recommendations[0].needs_human_review is True
    assert len(report.scenarios) == 3


def test_llm_malformed_json_falls_back():
    store = _build_store()

    def bad_llm(system, user):
        return "抱歉，我无法完成分析"

    agent = RiskAnalysisAgent(vector_store=store, search_client=DummySearchClient(), llm_call=bad_llm)
    report = agent.analyze(country="KZ")
    assert report.llm_unavailable is True
    assert report.key_risks
    assert any("规则引擎" in n for n in report.notes)


def test_extract_json_tolerates_fences():
    raw = '```json\n{"a": 1}\n```'
    assert _extract_json(raw) == {"a": 1}
    raw2 = '前言{"b": [1, 2]}后记'
    assert _extract_json(raw2) == {"b": [1, 2]}
