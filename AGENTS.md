# 仓库指南

本仓库是"AI+地缘政治风险高校挑战赛"赛道 B 项目的工作空间：以三一重工为模板，面向出海企业构建海外项目国别风险分析产品。赛事指南与团队决策优先于本文件。

## 项目结构与模块组织

- `asset/`：原始素材——`guide.pdf`（活动指南）、`enterprise_examples.docx`（企业模板），仅作只读引用。
- `PROJECT_NOTES.md`：团队决策、偏好、约束与关键时间节点，最先阅读。
- `app/`（规划中）：产品源码（网页应用或智能体）。
- `data/`（规划中）：结构化国别风险知识库（CSV/JSON）。
- `tests/`（规划中）：自动化测试。
- `docs/`（规划中）：PPT、README、运行说明。
- `tmp/`：临时与中间文件，不入库。

## 构建、测试与开发命令

项目处于规划阶段，尚无构建系统。计划采用的工作流：

```bash
python -m venv .venv
pip install -r requirements.txt
streamlit run app/app.py        # 或：uvicorn app.main:app --reload
pytest                          # 运行全部测试
```

## 编码风格与命名规范

- Python：4 空格缩进，遵循 PEP 8；文件、函数、变量使用 `snake_case`。
- 数据文件：小写 `snake_case`（如 `country_risk.csv`）；跨数据集使用稳定的国家/地区标识。
- 文档与注释可使用中文（团队语言）；标题与对外文本保持一致。
- 优先简洁、可读的实现，不堆复杂架构。

## 测试指南

- 使用 `pytest`；测试文件命名为 `test_*.py`，测试函数命名为 `test_<功能>`。
- 至少覆盖：风险评分规则、知识库数据完整性、LLM 输出解析。
- 每个真实案例验证场景都需添加回归测试。

## 提交与 Pull Request 指南

- 目前无 Git 历史；采用 Conventional Commits：`feat:`、`fix:`、`docs:`、`test:`、`chore:`。
- 提交保持小而聚焦，一次只做一件事。
- PR 必须说明改了什么、为什么，关联相关 issue；UI 变更需附截图。
- 严禁提交 API Key、密码等敏感凭证。

## 面向 Agent 的说明

- 设计与开发前先读 `PROJECT_NOTES.md` 与 `asset/guide.pdf`。
- 赛道 B 约束：系统必须可运行并具备至少一条完整核心流程，静态界面不算；PPT 不超过 20 页；评审看重能否解决真实问题，而非技术复杂度。
- 所有 AI 生成内容须展示来源、置信度与需要人工核实的事项。
- 不得在本工作区之外创建或修改文件。
