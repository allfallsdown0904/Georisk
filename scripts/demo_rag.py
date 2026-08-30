"""离线演示脚本：不依赖 FastAPI，直接运行风险分析智能体。

用法（在仓库根目录执行）：
    python scripts/demo_rag.py RS "三一重能塞尔维亚 Alibunar 168MW 风电项目" "当前政局动荡对项目进度有什么影响？"

默认规则引擎模式（无需任何 API Key）；配置 LLM_API_KEY / TAVILY_API_KEY 后自动升级。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from app.rag.agent import RiskAnalysisAgent, default_llm_call
from app.rag.search import get_search_client
from app.rag.vector_store import RiskVectorStore


def main() -> None:
    parser = argparse.ArgumentParser(description="地缘风险分析智能体演示")
    parser.add_argument("country", help="国家代码（KZ / NG / RS）")
    parser.add_argument("project", nargs="?", default="", help="项目/业务背景")
    parser.add_argument("question", nargs="?", default="", help="用户问题")
    parser.add_argument("--store", default="data/vector_store.json", help="向量库文件")
    parser.add_argument("--out", default="", help="报告输出 JSON 路径（默认仅打印）")
    args = parser.parse_args()

    if not os.path.exists(args.store):
        print("向量库不存在，请先运行: python scripts/build_vector_db.py", file=sys.stderr)
        raise SystemExit(1)

    store = RiskVectorStore(path=args.store)
    llm_call = default_llm_call if os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY") else None
    search_client = get_search_client()
    agent = RiskAnalysisAgent(vector_store=store, search_client=search_client, llm_call=llm_call)

    report = agent.analyze(country=args.country, project=args.project, question=args.question)
    data = report.to_dict()

    print(f"\n=== {data['country']} 国别风险分析 ===")
    print(f"总体风险: {data['overall_risk']}（{data['overall_score']} 分）"
          + (" [LLM 模式]" if not data["llm_unavailable"] else " [规则引擎模式]"))
    print("\n-- 维度评分 --")
    for key, dim in data["dimensions"].items():
        print(f"  {dim['name']}: {dim['score']} ({dim['level']}) - {dim['summary'][:40]}")
    print("\n-- 关键风险 --")
    for r in data["key_risks"][:5]:
        print(f"  [{r['likelihood']}] {r['risk']} (证据: {','.join(r.get('evidence', []))})")
    print("\n-- 建议 --")
    for rec in data["recommendations"][:5]:
        mark = "需人工核实" if rec["needs_human_review"] else ""
        print(f"  [{rec['priority']}] {rec['action']} {mark}")
    print("\n-- 情景 --")
    for s in data["scenarios"]:
        print(f"  {s['name']}: {s['summary'][:60]}")
    print("\n-- 来源 --")
    for src in data["sources"][:8]:
        print(f"  {src['type']} | {src['source']} | {src['url']}")

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        print(f"\n报告已保存: {os.path.abspath(args.out)}")


if __name__ == "__main__":
    main()
