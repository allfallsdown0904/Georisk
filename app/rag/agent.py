"""可复用的地缘风险分析智能体。

工作流：
1. 检索：从后台向量知识库（RiskVectorStore）检索与目标国/项目/问题最相关的事实；
2. 联网补强：调用搜索客户端（Tavily 等）获取最新信号，补充知识库时效性不足的问题；
3. 生成：优先由 LLM 综合知识库事实 + 联网信号，输出带证据、置信度、
   待人工核实标注的个性化建议与情景推演；LLM 不可用时退化为规则引擎。
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import urllib.error
import urllib.request
from typing import Callable

from app.rag.schemas import DIMENSIONS, Recommendation, RiskFact, RiskReport, Scenario, SearchResult, risk_level
from app.rag.search import DummySearchClient, SearchClient
from app.rag.vector_store import RiskVectorStore

COUNTRY_NAMES = {
    "KZ": "哈萨克斯坦",
    "NG": "尼日利亚",
    "RS": "塞尔维亚",
}

# 维度权重（退出与沉没成本对短期决策影响较小）
DIMENSION_WEIGHTS = {
    "politics": 0.25,
    "finance": 0.25,
    "policy": 0.2,
    "society": 0.2,
    "exit": 0.1,
}


def default_llm_call(system: str, user: str, temperature: float = 0.2, timeout: int = 60) -> str:
    """默认 LLM 调用：OpenAI 兼容 chat/completions（DeepSeek 等）。

    环境变量（兼容多种命名）：
    - LLM_API_KEY / DEEPSEEK_API_KEY
    - LLM_BASE_URL / DEEPSEEK_BASE_URL（默认 https://api.deepseek.com/v1）
    - LLM_MODEL / DEEPSEEK_MODEL（默认 deepseek-chat）
    """
    api_key = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("未配置 LLM_API_KEY / DEEPSEEK_API_KEY")
    base_url = (os.getenv("LLM_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL") or os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"
    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "stream": False,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"LLM 调用失败: {exc}") from exc
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"LLM 返回格式异常: {data}") from exc


def _extract_json(text: str) -> dict:
    """从 LLM 输出中稳健提取 JSON 对象（容忍 ``` 围栏与前后杂文本）。"""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM 输出中未找到 JSON 对象")
    return json.loads(text[start : end + 1])


class RiskAnalysisAgent:
    def __init__(
        self,
        vector_store: RiskVectorStore,
        search_client: SearchClient | None = None,
        llm_call: Callable[[str, str], str] | None = None,
    ):
        self.store = vector_store
        self.search_client = search_client or DummySearchClient()
        self.llm_call = llm_call

    # ---------------------------------------------------------------- 主入口
    def analyze(
        self,
        country: str,
        project: str = "",
        question: str = "",
        top_k: int = 10,
        web_queries: list[str] | None = None,
        max_web_results: int = 5,
    ) -> RiskReport:
        country_code = country.strip().upper()
        country_name = COUNTRY_NAMES.get(country_code, country_code)
        notes: list[str] = []

        # 1) 向量知识库检索
        query = " ".join(part for part in [country_name, project, question, "地缘政治风险"] if part)
        hits = self.store.search(query, top_k=top_k, country=country_code)
        facts = [fact for fact, _sim in hits]

        # 2) 联网搜索补强
        web_results: list[SearchResult] = []
        if not isinstance(self.search_client, DummySearchClient):
            queries = web_queries or [
                f"{country_name} {question}" if question else f"{country_name} 地缘政治风险",
                f"{country_name} 投资风险 政治 经济 2025",
                f"{country_name} 三一重工 工程机械 项目",
            ]
            seen: set[str] = set()
            for q in queries:
                try:
                    results = self.search_client.search(q, max_results=max_web_results)
                except Exception as exc:  # 搜索失败不阻断主流程
                    notes.append(f"联网搜索失败（{q}）: {exc}")
                    continue
                for item in results:
                    if item.url and item.url not in seen:
                        seen.add(item.url)
                        web_results.append(item)
            if not web_results:
                notes.append("联网搜索未返回结果，报告基于知识库事实生成")

        # 3) 生成报告（LLM 优先，规则引擎兜底）
        llm_unavailable = False
        if self.llm_call is not None:
            try:
                report = self._synthesize_with_llm(
                    country_code=country_code,
                    country_name=country_name,
                    project=project,
                    question=question,
                    facts=facts,
                    web_results=web_results,
                )
            except Exception as exc:
                notes.append(f"LLM 生成失败，已切换规则引擎: {exc}")
                llm_unavailable = True
                report = self._synthesize_rule_based(country_name, project, facts)
        else:
            llm_unavailable = True
            notes.append("未配置 LLM，当前为规则引擎模式（可配置 LLM_API_KEY 获得个性化生成）")
            report = self._synthesize_rule_based(country_name, project, facts)

        report.llm_unavailable = llm_unavailable
        report.notes = notes + getattr(report, "notes", [])
        report.sources = self._collect_sources(facts, web_results)
        return report

    # ---------------------------------------------------------------- LLM 路径
    def _synthesize_with_llm(
        self,
        country_code: str,
        country_name: str,
        project: str,
        question: str,
        facts: list[RiskFact],
        web_results: list[SearchResult],
    ) -> RiskReport:
        fact_block = "\n".join(
            f"[{f.id}]（{DIMENSIONS.get(f.dimension, f.dimension)}，来源:{f.source}，"
            f"日期:{f.date or '未知'}，置信度:{f.confidence}）{f.title}：{f.text}"
            for f in facts
        )
        web_block = "\n".join(
            f"[web:{i}] {r.title}（{r.source or '未知来源'}，{r.date or '日期未知'}）{r.snippet}\n  URL: {r.url}"
            for i, r in enumerate(web_results)
        )
        system = (
            "你是为出海工程机械与装备企业（以三一重工为模板）服务的地缘政治风险分析师。"
            "你只依据提供的知识库事实与联网检索结果分析，不得编造事实；"
            "每条判断必须标注证据引用（[事实id] 或 [web:序号]）、置信度（0-1）与是否需要人工核实。"
            "输出必须是严格 JSON，不要输出任何额外文字。"
        )
        user = (
            f"国家：{country_name}（{country_code}）\n"
            f"项目/业务背景：{project or '一般工程机械销售与服务'}\n"
            f"用户问题：{question or '请评估该国当前地缘政治与国别风险，并给出针对性建议'}\n\n"
            f"## 知识库事实\n{fact_block or '（无相关事实）'}\n\n"
            f"## 最新联网检索信号\n{web_block or '（无）'}\n\n"
            "请按以下 JSON 结构输出：\n"
            "{\n"
            '  "overall_risk": "低|中|高",\n'
            '  "overall_score": 0-100 数值,\n'
            '  "dimensions": {"politics": {"score": 0-100, "summary": "..."}, "finance": {...}, "policy": {...}, "society": {...}, "exit": {...}},\n'
            '  "key_risks": [{"risk": "风险描述", "impact": "对项目/业务的影响", "likelihood": "高|中|低", '
            '"evidence": ["事实id 或 web:n"], "confidence": 0.0-1.0, "needs_human_review": true}],\n'
            '  "scenarios": [{"name": "乐观情景|基准情景|压力情景", "summary": "...", "triggers": ["触发条件"]}],\n'
            '  "recommendations": [{"action": "建议动作", "priority": "高|中|低", "timeframe": "时间窗口", '
            '"cost_estimate": "成本估算", "evidence": ["引用"], "confidence": 0.0-1.0, "needs_human_review": true}],\n'
            '  "watchlist": ["需持续跟踪的指标/事件"]\n'
            "}\n"
            "要求：建议必须针对上述项目/业务背景且可执行；区分风险与机会；"
            "对无法确证的信息一律标 needs_human_review=true。"
        )
        raw = self.llm_call(system, user)
        data = _extract_json(raw)
        return self._report_from_llm_dict(country_name, project, data)

    def _report_from_llm_dict(self, country_name: str, project: str, data: dict) -> RiskReport:
        dims = {}
        for key, label in DIMENSIONS.items():
            item = data.get("dimensions", {}).get(key) or {}
            score = float(item.get("score", 50))
            dims[key] = {
                "name": label,
                "score": score,
                "level": risk_level(score),
                "summary": str(item.get("summary", "")),
            }
        scenarios = [
            Scenario(
                name=str(s.get("name", "")),
                summary=str(s.get("summary", "")),
                triggers=[str(t) for t in s.get("triggers", [])],
            )
            for s in data.get("scenarios", [])
        ]
        recommendations = [
            Recommendation(
                action=str(r.get("action", "")),
                priority=str(r.get("priority", "中")),
                timeframe=str(r.get("timeframe", "")),
                cost_estimate=str(r.get("cost_estimate", "")),
                evidence=[str(e) for e in r.get("evidence", [])],
                confidence=float(r.get("confidence", 0.5)),
                needs_human_review=bool(r.get("needs_human_review", True)),
            )
            for r in data.get("recommendations", [])
        ]
        score = float(data.get("overall_score", 50))
        return RiskReport(
            country=country_name,
            project=project,
            generated_at=_dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            overall_risk=str(data.get("overall_risk", risk_level(score))),
            overall_score=score,
            dimensions=dims,
            key_risks=[dict(r) for r in data.get("key_risks", [])],
            scenarios=scenarios,
            recommendations=recommendations,
            watchlist=[str(w) for w in data.get("watchlist", [])],
        )

    # ---------------------------------------------------------------- 规则引擎兜底
    def _synthesize_rule_based(self, country_name: str, project: str, facts: list[RiskFact]) -> RiskReport:
        by_dim: dict[str, list[RiskFact]] = {}
        for fact in facts:
            by_dim.setdefault(fact.dimension, []).append(fact)

        dims: dict[str, dict] = {}
        weighted_sum = 0.0
        weight_total = 0.0
        for key, label in DIMENSIONS.items():
            items = by_dim.get(key, [])
            if items:
                # 置信度加权平均，并略微上浮（风险场景建议保守）
                total = sum(f.score * f.confidence for f in items)
                conf = sum(f.confidence for f in items)
                score = round(total / conf if conf else 50.0, 1)
            else:
                score = 50.0
            dims[key] = {
                "name": label,
                "score": score,
                "level": risk_level(score),
                "summary": "；".join(f.title for f in items[:2]) if items else "知识库暂无该维度事实",
            }
            weighted_sum += score * DIMENSION_WEIGHTS[key]
            weight_total += DIMENSION_WEIGHTS[key]
        overall = round(weighted_sum / weight_total, 1) if weight_total else 50.0

        top = sorted(facts, key=lambda f: f.score * f.confidence, reverse=True)[:5]
        key_risks = [
            {
                "risk": f.title,
                "impact": f.text,
                "likelihood": "高" if f.score >= 70 else "中" if f.score >= 40 else "低",
                "evidence": [f.id],
                "confidence": round(f.confidence, 2),
                "needs_human_review": True,
            }
            for f in top
        ]
        scenarios = self._default_scenarios(country_name, facts)
        recommendations = self._default_recommendations(facts, project)
        watchlist = [
            f"{f.title}（{f.source}，{f.date or '日期未知'}）"
            for f in sorted(facts, key=lambda f: f.date or "", reverse=True)[:5]
        ]
        return RiskReport(
            country=country_name,
            project=project,
            generated_at=_dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            overall_risk=risk_level(overall),
            overall_score=overall,
            dimensions=dims,
            key_risks=key_risks,
            scenarios=scenarios,
            recommendations=recommendations,
            watchlist=watchlist,
        )

    def _default_scenarios(self, country_name: str, facts: list[RiskFact]) -> list[Scenario]:
        high = [f for f in facts if f.score >= 60]
        triggers = [f.title for f in sorted(high, key=lambda f: f.score, reverse=True)[:3]]
        return [
            Scenario(
                name="乐观情景",
                summary=f"{country_name} 政策环境改善、汇率企稳、社会矛盾缓和，项目按计划推进。",
                triggers=["政局稳定且选举/交接顺利", "汇率与通胀回落", "监管改革落地"],
            ),
            Scenario(
                name="基准情景",
                summary=f"{country_name} 延续当前态势：风险可控但需持续监控，项目可推进但须做好合规与本地化。",
                triggers=triggers or ["主要风险指标保持现状"],
            ),
            Scenario(
                name="压力情景",
                summary=f"{country_name} 突发政治/社会/金融冲击，项目进度与回款受到实质性影响。",
                triggers=["大规模社会动荡或政权更迭", "汇率大幅贬值或资本管制", "针对中国企业的制裁/政策逆转"],
            ),
        ]

    def _default_recommendations(self, facts: list[RiskFact], project: str) -> list[Recommendation]:
        evidence = [f.id for f in facts[:4]]
        high_dim = [k for k, v in DIMENSIONS.items() if any(f.dimension == k and f.score >= 70 for f in facts)]
        actions: list[Recommendation] = []
        if "finance" in high_dim or any(f.dimension == "finance" and f.score >= 60 for f in facts):
            actions.append(
                Recommendation(
                    action="针对汇率风险建立套保机制（远期/期权），合同尽量以硬通货计价或锁定汇率条款；分批换汇、保留当地币应急头寸。",
                    priority="高",
                    timeframe="1-3 个月",
                    cost_estimate="套保成本约为合同金额的 1%-3%",
                    evidence=[f.id for f in facts if f.dimension == "finance"][:3],
                    confidence=0.7,
                    needs_human_review=True,
                )
            )
        if "policy" in high_dim or any(f.dimension == "policy" and f.score >= 60 for f in facts):
            actions.append(
                Recommendation(
                    action="聘请本地律所/税务顾问复核新税制与投资优惠适用性，确保增值税、关税与劳工合规；跟踪政策窗口期。",
                    priority="高",
                    timeframe="1 个月内",
                    cost_estimate="本地顾问年费约 2-8 万美元",
                    evidence=[f.id for f in facts if f.dimension == "policy"][:3],
                    confidence=0.75,
                    needs_human_review=True,
                )
            )
        if "society" in high_dim or any(f.dimension == "society" and f.score >= 60 for f in facts):
            actions.append(
                Recommendation(
                    action="完善项目安保预案：驻地安全评估、人员保险、撤离预案；与中资商会、使领馆建立联络；监控罢工与游行热点区域。",
                    priority="高",
                    timeframe="持续",
                    cost_estimate="安保预算约占项目成本 1%-5%",
                    evidence=[f.id for f in facts if f.dimension == "society"][:3],
                    confidence=0.7,
                    needs_human_review=True,
                )
            )
        if "politics" in high_dim or any(f.dimension == "politics" and f.score >= 60 for f in facts):
            actions.append(
                Recommendation(
                    action="建立地缘政治事件监测（大选、制裁、大国博弈），避免在敏感节点集中投入；关键合同加入不可抗力与制裁条款。",
                    priority="中",
                    timeframe="1-3 个月",
                    cost_estimate="监测与法务成本较低",
                    evidence=[f.id for f in facts if f.dimension == "politics"][:3],
                    confidence=0.7,
                    needs_human_review=True,
                )
            )
        if not actions:
            actions.append(
                Recommendation(
                    action="维持现有推进节奏，但建立季度国别风险复评机制，持续跟踪汇率、政策与社会动态。",
                    priority="中",
                    timeframe="季度",
                    cost_estimate="低",
                    evidence=evidence,
                    confidence=0.6,
                    needs_human_review=True,
                )
            )
        return actions

    # ---------------------------------------------------------------- 溯源
    def _collect_sources(self, facts: list[RiskFact], web_results: list[SearchResult]) -> list[dict]:
        sources: dict[str, dict] = {}
        for f in facts:
            key = f.source_url or f.source
            sources[key] = {
                "type": "knowledge_base",
                "fact_id": f.id,
                "title": f.title,
                "source": f.source,
                "url": f.source_url,
                "date": f.date,
                "confidence": f.confidence,
            }
        for i, r in enumerate(web_results):
            sources[r.url or f"web:{i}"] = {
                "type": "web_search",
                "fact_id": f"web:{i}",
                "title": r.title,
                "source": r.source,
                "url": r.url,
                "date": r.date,
                "confidence": 0.4,  # 联网结果默认低置信度，需人工核实
            }
        return list(sources.values())
