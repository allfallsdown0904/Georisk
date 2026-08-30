# data/ 目录说明

| 文件/目录 | 说明 |
| --- | --- |
| `countries.csv` | 支持的国家清单与基础信息 |
| `risk_indicators.csv` | 风险指标口径（五维：政局与地缘冲突 / 金融与外汇 / 政策与法规 / 社会与安全秩序 / 退出与沉没成本） |
| `seed/*_risk_facts.json` | 国别风险事实种子数据（人工整理、带来源与置信度），是向量知识库的事实来源 |
| `vector_store.json` | 向量知识库构建产物（由 `python scripts/build_vector_db.py` 生成），提交入库以便离线直接运行 |

更新流程：修改 `seed/*.json` → 运行 `python scripts/build_vector_db.py` → 提交新产物。
