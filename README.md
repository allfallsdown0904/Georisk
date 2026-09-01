# Georisk 海外项目国别风险分析

> 吊哥是区 white是区 杨桃是神

北京大学"AI+地缘政治风险高校挑战赛"赛道 B 项目：以三一重工为模板，面向出海企业构建海外项目国别风险分析产品。当前为骨架阶段。

## 目录结构

- `app/`：FastAPI 后端与静态前端
- `data/`：国别风险知识库（CSV，当前为示例占位数据）
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
