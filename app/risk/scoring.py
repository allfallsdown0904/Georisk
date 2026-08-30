"""示例评分规则：维度分=指标分均值，综合分=维度分均值；分数越高风险越高。"""
from app.data_loader import load_countries, load_risk_indicators
from app.risk.schema import CountryRiskProfile, RiskDimension

DIMENSION_NAMES = {
    "politics_conflict": "政局与冲突",
    "finance_fx": "金融与外汇",
    "policy_regulation": "政策与法规",
    "social_order": "社会与秩序",
    "exit_sunk": "退出与沉没成本",
}


def score_to_level(score: float) -> str:
    if score < 40:
        return "低"
    if score < 70:
        return "中"
    return "高"


def build_profile(country_code: str) -> CountryRiskProfile:
    countries = {c["code"]: c for c in load_countries()}
    if country_code not in countries:
        raise KeyError(country_code)

    by_dim: dict[str, list[dict]] = {}
    for row in load_risk_indicators(country_code):
        by_dim.setdefault(row["dimension"], []).append(row)

    dimensions: list[RiskDimension] = []
    for key, name in DIMENSION_NAMES.items():
        rows = by_dim.get(key, [])
        if not rows:
            continue
        score = round(sum(float(r["score"]) for r in rows) / len(rows), 1)
        dimensions.append(
            RiskDimension(
                key=key,
                name=name,
                score=score,
                level=score_to_level(score),
                evidence=[f"{r['indicator']}: {r['value']}（{r['evidence']}）" for r in rows],
                sources=[r["source"] for r in rows],
            )
        )

    overall = round(sum(d.score for d in dimensions) / len(dimensions), 1) if dimensions else 0.0
    return CountryRiskProfile(
        country_code=country_code,
        country_name=countries[country_code]["name_zh"],
        overall_score=overall,
        overall_level=score_to_level(overall),
        dimensions=dimensions,
    )
