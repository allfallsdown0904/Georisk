"""风险画像相关数据模型。"""
from pydantic import BaseModel, Field


class RiskDimension(BaseModel):
    key: str
    name: str
    score: float = Field(ge=0, le=100)
    level: str
    evidence: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class CountryRiskProfile(BaseModel):
    country_code: str
    country_name: str
    overall_score: float = Field(ge=0, le=100)
    overall_level: str
    dimensions: list[RiskDimension]


class AnalyzeRequest(BaseModel):
    country_code: str
    project_type: str = "EPC工程总承包"


class AnalyzeResponse(BaseModel):
    country_code: str
    project_type: str
    analysis: str
    model: str


class ApiKeyRequest(BaseModel):
    api_key: str = Field(min_length=1, max_length=4096)


class ApiConfigStatus(BaseModel):
    configured: bool
    source: str | None = None
    model: str
    saved_to: str | None = None
