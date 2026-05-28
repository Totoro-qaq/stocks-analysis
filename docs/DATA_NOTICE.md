# 数据说明 / Data Notice

本仓库有意不包含下载行情、ETF 持仓文件、派生分析 CSV/JSON 输出、生成报告、日志或演示录屏。

This repository intentionally does not include downloaded market data, ETF holdings files, generated analysis CSV/JSON outputs, generated reports, logs, or demo recordings.

## 为什么排除数据 / Why Data Is Excluded

项目可以从 Yahoo Finance、State Street SPDR 资源、Sina Finance 等第三方来源获取或派生数据。这些供应商可能限制数据再分发、数据库创建或公开复用。为降低公开仓库风险，供应商数据和派生研究输出均只保留在本地。

The project can fetch or derive data from third-party sources such as Yahoo Finance, State Street SPDR resources, and Sina Finance. Those providers may restrict redistribution, database creation, or public reuse of their data and site content. To keep the public repository low-risk, all provider data and derived research outputs remain local-only.

排除路径包括：

Excluded paths include:

- `data/raw/*`
- `data/processed/*`
- `data/output/*`
- `sina_crawler/*`
- `frontend/public/demo/*.gif`
- `.recordings/*`
- `logs/*`

仓库只提交源代码、配置模板、文档和空目录占位文件。

Only source code, configuration templates, documentation, and empty directory placeholders are committed.

## 复现输出 / Reproducing Outputs

创建本地环境文件：

Create a local environment file:

```powershell
Copy-Item config/.env.example config/.env
```

本地重新生成数据和输出：

Regenerate data and outputs locally:

```powershell
python src/fetch_market_data.py --summary-only
python src/build_universe_50.py
python src/analysis_engine.py
python src/portfolio_optimization.py
python src/walk_forward.py
python src/stat_tests.py
```

使用、发布或分享生成数据前，请自行审查并遵守当前数据源供应商条款。

Before using, publishing, or sharing generated datasets, review and comply with the source providers' current terms.
