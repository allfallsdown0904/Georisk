"""加载 data/ 目录下的国别风险知识库（CSV/JSON）。"""
import json
from pathlib import Path
from typing import Any

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
COUNTRIES_CSV = DATA_DIR / "countries.csv"
RISK_INDICATORS_CSV = DATA_DIR / "risk_indicators.csv"


def _read_table(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    df = pd.read_csv(path, encoding="utf-8")
    return df.to_dict(orient="records")


def load_countries() -> list[dict[str, Any]]:
    """返回国家列表，字段：code、name_zh、name_en、region。"""
    return _read_table(COUNTRIES_CSV)


def load_risk_indicators(country_code: str | None = None) -> list[dict[str, Any]]:
    """返回风险指标行，可按国家代码过滤。"""
    rows = _read_table(RISK_INDICATORS_CSV)
    if country_code:
        rows = [r for r in rows if r["country_code"] == country_code]
    return rows
