# 向量知识库与风险分析智能体设计说明

## 1. 目标

实现一个**可复用**的地缘风险分析智能体：

1. 基于后台**向量数据库**检索国别风险事实（`app/rag/vector_store.py`）；
2. 调用**联网搜索 API** 补充最新信号（`app/rag/search.py`，默认 Tavily）；
3. 结合项目/企业背景生成**个性化建议**，每条判断带证据引用、置信度与"待人工核实"标注（`app/rag/agent.py`）。

## 2. 架构

```
用户问题(国家/项目/问题)
        │
        ▼
┌────────────────────────────────────────────┐
│ RiskAnalysisAgent.analyze()                │
│  ① 向量检索：RiskVectorStore.search()      │ ← data/vector_store.json
│  ② 联网补强：SearchClient（Tavily/离线）    │ ← env: TAVILY_API_KEY
│  ③ 生成：LLM 综合(DeepSeek) → 规则引擎兜底  │ ← env: LLM_API_KEY
└────────────────────────────────────────────┘
        │
        ▼
  RiskReport（总体风险/维度评分/情景推演/建议清单/证据溯源）
```

模块职责：

| 文件 | 职责 |
| --- | --- |
| `app/rag/schemas.py` | 数据模型（RiskFact / SearchResult / Scenario / Recommendation / RiskReport）与风险分级规则 |
| `app/rag/embeddings.py` | 向量化：本地哈希嵌入（零依赖兜底）+ OpenAI 兼容嵌入 API（可选） |
| `app/rag/vector_store.py` | 向量库：JSON 持久化、按国家/维度过滤的余弦检索 |
| `app/rag/search.py` | 联网搜索客户端抽象：Tavily 实现 + 离线兜底 |
| `app/rag/agent.py` | 智能体编排：检索 → 搜索 → LLM/规则生成，统一输出报告 |
| `app/rag/router.py` | FastAPI 路由（`/api/rag/*`） |
| `data/seed/*.json` | 国别风险事实种子数据（人工整理、带来源） |
| `scripts/build_vector_db.py` | 从种子数据构建 `data/vector_store.json` |

## 3. 数据流与个性化逻辑

- **检索**：查询串 = 国家名 + 项目背景 + 用户问题；向量库按余弦相似度返回 top-k 事实。
- **联网补强**：默认生成 3 条搜索词（国别风险、投资风险、三一在该国业务），结果以 `[web:n]` 编号进入上下文与溯源列表；搜索失败不阻断主流程。
- **生成**：
  - LLM 模式：系统提示限定"只依据给定事实与检索结果"，输出严格 JSON（总体风险、五维评分、关键风险、三情景、建议清单、观察清单）；JSON 解析失败自动降级。
  - 规则引擎模式（无 Key/离线演示）：按置信度加权计算各维度与总体评分，从命中事实生成建议，保证 MVP 在无外部依赖下可演示。
- **个性化**：提示词与建议模板都注入项目背景与三一业务场景（如哈萨克斯坦本地化产线、尼日利亚宗格鲁水电站、塞尔维亚 Alibunar 风电）。
- **溯源与人工核实**：报告 `sources` 列出知识库事实与联网结果的来源/URL/日期/置信度；LLM 未确证信息强制 `needs_human_review=true`。

## 4. 配置（环境变量）

| 变量 | 用途 | 默认 |
| --- | --- | --- |
| `LLM_API_KEY` / `DEEPSEEK_API_KEY` | LLM 生成密钥 | 无（不配置则规则引擎） |
| `LLM_BASE_URL` / `DEEPSEEK_BASE_URL` | LLM 服务地址 | `https://api.deepseek.com/v1` |
| `LLM_MODEL` / `DEEPSEEK_MODEL` | 模型名 | `deepseek-chat` |
| `EMBEDDING_API_KEY` | 远程嵌入密钥（可选） | 无（使用本地哈希嵌入） |
| `EMBEDDING_BASE_URL` | 嵌入服务地址 | `https://api.deepseek.com/v1` |
| `EMBEDDING_MODEL` | 嵌入模型 | `text-embedding-3-small` |
| `TAVILY_API_KEY` | 联网搜索密钥（Tavily） | 无（自动离线模式） |
| `SEARCH_PROVIDER` | `tavily` / `none` | `tavily` |

## 5. 运行方式

```bash
# 1) 首次或更新种子数据后，构建向量库
python scripts/build_vector_db.py

# 2) 单元测试
python -m pytest tests/test_embeddings.py tests/test_vector_store.py tests/test_search.py tests/test_agent.py -v

# 3) 启动服务（路由已 include 后）
uvicorn app.main:app --reload

# 4) 调用示例
curl -X POST http://127.0.0.1:8000/api/rag/analyze \
  -H "Content-Type: application/json" \
  -d '{"country": "RS", "project": "三一重能塞尔维亚 Alibunar 168MW 风电项目（2028 年投运，25 年运维）", "question": "当前政局动荡对项目进度有什么影响？"}'

curl http://127.0.0.1:8000/api/rag/health
curl http://127.0.0.1:8000/api/rag/facts?country=KZ
```

## 6. 扩展与替换

- **更换向量库**：保持 `RiskVectorStore` 接口不变，内部替换为 ChromaDB / FAISS / Milvus 即可，智能体与路由无需改动。
- **更换搜索引擎**：实现 `SearchClient` 协议（如 Bing / Serper / 本地 RSS），在 `get_search_client()` 注册。
- **新增国家**：在 `data/seed/` 添加 `<ISO3>_risk_facts.json`（字段见 `data/seed/kz_risk_facts.json`），在 `agent.py` 的 `COUNTRY_NAMES` 注册中文名，重新构建向量库。
- **维度调整**：修改 `DIMENSIONS` 与 `DIMENSION_WEIGHTS`（`schemas.py` / `agent.py`），无需改动其余模块。

## 7. 已知边界

- 本地哈希嵌入为语义近似，追求更高检索质量时配置 `EMBEDDING_API_KEY`。
- 联网结果默认置信度 0.4，一律建议人工核实后再用于决策。
- 种子数据为 2025 年公开信源整理，需按 `docs/` 计划周期性刷新（配合 `data/` 版本管理）。
