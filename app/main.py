"""FastAPI 入口：API 路由 + 静态前端托管。"""
from ipaddress import ip_address
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles

from app import config
from app.data_loader import load_countries
from app.llm.client import analyze_country
from app.risk.schema import AnalyzeRequest, AnalyzeResponse, ApiConfigStatus, ApiKeyRequest
from app.risk.scoring import build_profile
from app.rag.router import router as rag_router

app = FastAPI(title="Georisk 海外项目国别风险分析", version="0.1.0")

app.include_router(rag_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/countries")
def list_countries() -> dict:
    return {"countries": load_countries()}


@app.get("/api/config/status", response_model=ApiConfigStatus)
def config_status() -> ApiConfigStatus:
    return ApiConfigStatus(
        configured=bool(config.get_api_key()),
        source=config.api_key_source(),
        model=config.DEEPSEEK_MODEL,
    )


@app.post("/api/config/api-key", response_model=ApiConfigStatus)
def import_api_key(req: ApiKeyRequest, request: Request) -> ApiConfigStatus:
    client_host = request.client.host if request.client else ""
    try:
        is_local = ip_address(client_host).is_loopback
    except ValueError:
        is_local = client_host == "testclient"
    if not is_local:
        raise HTTPException(status_code=403, detail="仅允许从本机页面导入 API Key")
    try:
        saved_path = config.save_api_key(req.api_key)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"API Key 保存失败：{exc}") from exc
    return ApiConfigStatus(
        configured=True,
        source="runtime_file",
        model=config.DEEPSEEK_MODEL,
        saved_to=str(saved_path.relative_to(config.PROJECT_ROOT)),
    )


@app.get("/api/risk/{country_code}")
def risk_profile(country_code: str) -> dict:
    try:
        profile = build_profile(country_code)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"未知国家代码：{country_code}")
    return profile.model_dump()


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    if not config.get_api_key():
        raise HTTPException(status_code=503, detail="未配置 API Key，请点击网页右上角“导入 API”")
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
