"""从 data/seed/*.json 构建向量知识库并持久化到 data/vector_store.json。

用法（在仓库根目录执行）：
    python scripts/build_vector_db.py [--seed-dir data/seed] [--out data/vector_store.json]

构建结果已入库，普通运行无需重复执行；仅在更新种子数据后需要重建。
"""

from __future__ import annotations

import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from app.rag.embeddings import get_embedder
from app.rag.vector_store import RiskVectorStore


def main() -> None:
    parser = argparse.ArgumentParser(description="构建国别风险向量知识库")
    parser.add_argument("--seed-dir", default="data/seed", help="种子数据目录（JSON 文件）")
    parser.add_argument("--out", default="data/vector_store.json", help="输出向量库文件")
    args = parser.parse_args()

    seed_dir = os.path.abspath(args.seed_dir)
    if not os.path.isdir(seed_dir):
        raise SystemExit(f"种子目录不存在: {seed_dir}")

    embedder = get_embedder()
    store = RiskVectorStore.build_from_seed(seed_dir, embedder=embedder, save_path=args.out)
    print(f"知识库构建完成：共 {len(store)} 条事实，国家：{store.list_countries()}")
    print(f"向量库已保存至: {os.path.abspath(args.out)}")
    print(f"嵌入器: {type(embedder).__name__}")


if __name__ == "__main__":
    main()
