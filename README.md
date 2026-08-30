# Georisk 海外项目国别风险分析

> 吊哥是区 white是区 杨桃是神

北京大学"AI+地缘政治风险高校挑战赛"赛道 B 项目：以三一重工为模板，面向出海企业构建海外项目国别风险分析产品。当前已具备可运行 MVP：风险画像 + RAG 智能体分析（事件预警/情景推演/建议清单）。

## 目录结构

- `app/`：FastAPI 后端与静态前端
- `data/`：国别风险知识库（`countries.csv` / `risk_indicators.csv` 指标 + `seed/*_risk_facts.json` 种子事实，`vector_store.json` 为向量库构建产物）
- `tests/`：pytest 测试
- `docs/`：竞赛交付材料（PPT、演示脚本）
- `asset/`：赛事原始素材（指南与企业模板，只读）
- `PROJECT_NOTES.md` / `AGENTS.md`：项目决策与协作约定

## 配置环境并安装

```bash
conda create -n georisk python=3.12
conda activate georisk
pip install -r requirements.txt
```

## 配置

启动后可点击网页右上角“导入 API”，输入 DeepSeek API Key。系统会将 Key 保存为
`runtime/api_key.txt`（仅当前系统用户可读写），并立即启用；`runtime/` 已被 Git 忽略，
提交或打包项目前仍应再次确认其中不含密钥。为避免外部访客覆盖服务端 Key，网页导入接口
只接受来自 `127.0.0.1` / `::1` 的本机请求；公网部署请改用服务端环境变量或密钥管理服务。

也可以复制 `.env.example` 为 `.env` 并填入 DeepSeek API Key：

```bash
DEEPSEEK_API_KEY=sk-xxx
```

未配置 Key 时，除 `/api/analyze` 外的功能均可正常运行。

## 启动

```bash
uvicorn app.main:app --reload
```

浏览器访问 <http://127.0.0.1:8000>

## 测试

```bash
pytest
```

## API

- `GET /api/health`：服务状态
- `GET /api/countries`：国家列表
- `GET /api/risk/{country_code}`：国别风险画像（如 `KZ`）
- `POST /api/analyze`：LLM 分析，请求体 `{"country_code": "KZ", "project_type": "EPC工程总承包"}`，需配置 Key
- `GET /api/config/status`：检查 API 是否已配置（不返回 Key）
- `POST /api/config/api-key`：保存并立即启用 API Key，请求体 `{"api_key": "sk-xxx"}`

## 风险分析智能体（RAG）

系统内置可复用的国别风险分析智能体（`app/rag/`）：基于后台向量知识库检索，调用联网搜索 API 补强，输出带证据、置信度与"待人工核实"标注的个性化报告（含乐观/基准/压力三情景）。

### 构建向量库（更新种子数据后执行）

```bash
python scripts/build_vector_db.py
```

### 配置（.env）

```bash
# LLM 生成（任选其一；不配置则自动使用规则引擎）
LLM_API_KEY=sk-xxx            # 或 DEEPSEEK_API_KEY
LLM_MODEL=deepseek-chat

# 联网搜索（不配置则离线模式）
TAVILY_API_KEY=tvly-xxx
SEARCH_PROVIDER=tavily

# 可选：远程嵌入（不配置则使用本地哈希嵌入）
EMBEDDING_API_KEY=sk-xxx
```

### 页面与 API

- 网页：在"事件预警"页输入咨询问题并点击"开始智能分析"，情景推演/建议清单自动填充
- `POST /api/rag/analyze`：请求体 `{"country":"KZ","project":"矿山设备供应","question":"新税法对进口成本的影响"}`
- `GET /api/rag/health` / `GET /api/rag/facts?country=KZ`

### 离线演示

```bash
python scripts/demo_rag.py RS "三一重能 Alibunar 168MW 风电项目" "当前政局动荡对项目进度有什么影响？"
```

详细设计见 [docs/vector_db_design.md](docs/vector_db_design.md)。