# Georisk 海外项目国别风险分析

北京大学"AI+地缘政治风险高校挑战赛"赛道 B 项目：以三一重工为模板，面向出海企业构建海外项目国别风险分析产品。当前为骨架阶段。

## 目录结构

- `app/`：FastAPI 后端与静态前端
- `data/`：国别风险知识库（CSV，当前为示例占位数据）
- `tests/`：pytest 测试
- `docs/`：竞赛交付材料（PPT、演示脚本）
- `asset/`：赛事原始素材（指南与企业模板，只读）
- `PROJECT_NOTES.md` / `AGENTS.md`：项目决策与协作约定

## 安装

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 配置

复制 `.env.example` 为 `.env` 并填入 DeepSeek API Key：

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
