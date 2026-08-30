"""集成测试：验证智能体会真实发起对搜索 API 的 HTTP 调用并融合结果。"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.rag.agent import RiskAnalysisAgent
from app.rag.embeddings import HashEmbedder
from app.rag.schemas import RiskFact
from app.rag.search import TavilySearchClient
from app.rag.vector_store import RiskVectorStore


class FakeSearchHandler(BaseHTTPRequestHandler):
    """模拟一个返回 Tavily 格式 JSON 的搜索 API。"""

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        query = body.get("query", "")
        results = [
            {
                "title": f"搜索结果 {i}",
                "url": f"https://example.com/{i}",
                "content": f"{query} 的相关摘要 {i}",
                "published_date": "2025-11-01",
                "source": "示例源",
            }
            for i in range(2)
        ]
        payload = json.dumps({"results": results}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


def test_agent_calls_search_api_and_merges_results():
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeSearchHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        client = TavilySearchClient(api_key="test-key", endpoint=f"http://127.0.0.1:{port}/search")

        store = RiskVectorStore(embedder=HashEmbedder())
        store.add(
            RiskFact(
                id="rs-1",
                country="RS",
                dimension="politics",
                title="塞尔维亚持续抗议",
                text="大规模抗议影响项目工地周边秩序",
                source="测试来源",
                score=70,
                confidence=0.8,
            )
        )
        agent = RiskAnalysisAgent(vector_store=store, search_client=client)
        report = agent.analyze(country="RS", question="最新动态", web_queries=["塞尔维亚 抗议 2025"])

        web_sources = [s for s in report.sources if s["type"] == "web_search"]
        assert len(web_sources) == 2, "智能体应把搜索 API 返回的结果并入证据溯源"
        assert all(s["url"].startswith("https://example.com/") for s in web_sources)
        assert all(s["confidence"] == 0.4 for s in web_sources), "联网结果默认低置信度待核实"
        assert not any("联网搜索失败" in n for n in report.notes), "搜索成功时不应有失败提示"
        assert report.key_risks, "规则引擎仍应基于知识库生成关键风险"
        assert report.overall_risk in ("低", "中", "高")
    finally:
        server.shutdown()
        server.server_close()
