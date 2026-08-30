"""种子数据完整性测试：确保新增国家/事实不会破坏知识库质量。"""

import json
import os

import pytest

from app.rag.agent import COUNTRY_NAMES
from app.rag.schemas import DIMENSIONS

SEED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "seed")


def _seed_files() -> list[str]:
    return sorted(f for f in os.listdir(SEED_DIR) if f.endswith(".json"))


def test_all_seed_files_valid_and_covered():
    assert _seed_files(), "data/seed 下应有种子 JSON 文件"
    for fname in _seed_files():
        with open(os.path.join(SEED_DIR, fname), encoding="utf-8") as fh:
            payload = json.load(fh)
        code = payload["country"]
        assert code in COUNTRY_NAMES, f"{fname} 的国家代码 {code} 未在 agent.py COUNTRY_NAMES 注册"
        facts = payload["facts"]
        assert len(facts) >= 8, f"{fname} 事实数量偏少（{len(facts)}）"
        ids: set[str] = set()
        dims: set[str] = set()
        for f in facts:
            assert f["country"] == code, f"{fname} 中事实国家代码不一致"
            assert f["dimension"] in DIMENSIONS, f"{fname} 含未知维度 {f['dimension']}"
            assert f["id"] not in ids, f"{fname} 重复事实 id: {f['id']}"
            ids.add(f["id"])
            dims.add(f["dimension"])
            assert 0 <= f["score"] <= 100, f"{f['id']} 评分越界"
            assert 0 <= f["confidence"] <= 1, f"{f['id']} 置信度越界"
            assert f["title"] and f["text"] and f["source"], f"{f['id']} 缺少标题/正文/来源"
        assert dims == set(DIMENSIONS), f"{fname} 应覆盖全部五个维度，缺少 {set(DIMENSIONS) - dims}"


def test_vector_store_artifact_matches_seed():
    """向量库构建产物应与种子数据一致（防止只改种子忘记重建）。"""
    store_path = os.path.join(os.path.dirname(SEED_DIR), "vector_store.json")
    if not os.path.exists(store_path):
        pytest.skip("向量库产物不存在，可运行 scripts/build_vector_db.py 生成")
    with open(store_path, encoding="utf-8") as fh:
        payload = json.load(fh)
    expected = 0
    for fname in _seed_files():
        with open(os.path.join(SEED_DIR, fname), encoding="utf-8") as fh:
            expected += len(json.load(fh)["facts"])
    assert len(payload["facts"]) == expected, "向量库事实数与种子数据不一致，请重新运行 build_vector_db.py"
    assert len(payload["vectors"]) == expected, "向量库向量数与事实数不一致"
