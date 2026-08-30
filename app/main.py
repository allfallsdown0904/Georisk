"""FastAPI 入口：API 路由 + 静态前端托管。"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app import config
from app.data_loader import load_countries
from app.llm.client import analyze_country
from app.risk.schema import AnalyzeRequest, AnalyzeResponse
from app.risk.scoring import build_profile

app = FastAPI(title="Georisk 海外项目国别风险分析", version="0.1.0")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/countries")
def list_countries() -> dict:
    return {"countries": load_countries()}


@app.get("/api/risk/{country_code}")
def risk_profile(country_code: str) -> dict:
    try:
        profile = build_profile(country_code)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"未知国家代码：{country_code}")
    return profile.model_dump()


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    if not config.DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail="未配置 DEEPSEEK_API_KEY，请在 .env 中填写后重试")
    try:
        profile = build_profile(req.country_code)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"未知国家代码：{req.country_code}")
    summary = "\n".join(
        f"- {d.name}: {d.score} 分（{d.level}），依据：{'；'.join(d.evidence)}" for d in profile.dimensions
    )
    text = analyze_country(req.country_code, req.project_type, summary)
    return AnalyzeResponse(
        country_code=req.country_code,
        project_type=req.project_type,
        analysis=text,
        model=config.DEEPSEEK_MODEL,
    )


STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
