# 美股量化研究平台 / Stocks Analysis Platform

一个可复现的美股科技股量化研究平台，覆盖数据抓取、指标计算、组合优化、Walk-forward 验证、统计检验、人工规则干预、AI 辅助报告，以及 Vue + FastAPI 可视化看板。

A reproducible US stock quantitative research platform covering data ingestion, analytics, portfolio optimization, walk-forward validation, statistical testing, human rule overlays, AI-assisted reporting, and a Vue + FastAPI dashboard.

## 功能特性 / Features

- Yahoo Finance chart API 行情抓取与本地 CSV/MySQL 存储。
- 基于 XLK 相关科技股构建 50 股研究池。
- 单股风险收益、累计收益、布林带、相关性矩阵。
- 均值-方差组合优化、有效前沿、HRP、Black-Litterman、因子分析扩展。
- Walk-forward 样本外验证、t 检验、bootstrap 区间。
- 人工规则覆盖：排除、上限、下限、收益增强、风险惩罚、备注。
- FastAPI、Celery、Redis、MySQL、OpenTelemetry、Jaeger、Prometheus、Vue 前端。
- 可选 DeepSeek/OpenAI-compatible 报告生成与 Dify Workflow 集成。
- 仓库不提交下载行情、ETF 持仓、派生输出、日志或演示录屏，降低数据授权风险。

## 架构 / Architecture

```text
Market data -> CSV/MySQL -> Analytics -> Portfolio optimization
            -> Walk-forward validation -> Statistical tests
            -> FastAPI/Celery -> Vue dashboard -> Report output
```

## 目录结构 / Repository Layout

```text
backend/              FastAPI routers, services, Celery integration
frontend/             Vue 3 + Vite dashboard
src/                  Data ingestion and quantitative analysis scripts
data/                 Local-only datasets and generated outputs
config/               Environment templates and observability config
docs/                 Design notes, data dictionary, and project plans
scripts/              Demo recording and utility scripts
nginx/                Frontend container nginx config
docker-compose.yml    Full local stack
```

## 环境要求 / Requirements

- Python 3.12+
- Node.js 20+ 或 22+
- Docker Desktop + Docker Compose

## 配置 / Configuration

复制环境变量模板并填入本地密钥：

Copy the environment template and fill local secrets:

```powershell
Copy-Item config/.env.example config/.env
```

关键变量 / Important variables:

```text
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here
MYSQL_DATABASE=us_stock_mvp
REDIS_URL=redis://localhost:6379/0

DEEPSEEK_API_KEY=your_deepseek_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro

DIFY_BASE_URL=https://api.dify.ai/v1
DIFY_REPORT_API_KEY=
DIFY_RULES_API_KEY=
DIFY_USER=stocks-analysis-local
```

不要提交 `config/.env`。

Never commit `config/.env`.

## 数据与授权说明 / Data and Redistribution Notice

本仓库不提交下载行情、ETF 持仓、派生分析输出、本地报告、日志或演示录屏。详见 [docs/DATA_NOTICE.md](docs/DATA_NOTICE.md)。

Downloaded market data, ETF holdings, generated analytics, local reports, logs, and demo recordings are not committed. See [docs/DATA_NOTICE.md](docs/DATA_NOTICE.md).

## 本地开发 / Local Development

后端依赖 / Backend dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

前端依赖 / Frontend dependencies:

```powershell
cd frontend
npm ci
cd ..
```

启动本地前后端 / Run local backend and frontend:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 18000
cd frontend
npm run dev
```

启动完整 Docker 栈 / Run the full Docker stack:

```powershell
docker compose up -d --build
```

默认地址 / Default URLs:

- Frontend dev: `http://localhost:5173`
- Frontend Docker: `http://localhost:18080`
- Backend health: `http://localhost:18000/api/health`
- Jaeger: `http://localhost:16686`
- Prometheus: `http://localhost:19090`

## 分析脚本 / Analysis Scripts

在项目根目录运行：

Run from the project root:

```powershell
python src/fetch_market_data.py --summary-only
python src/build_universe_50.py
python src/analysis_engine.py
python src/portfolio_optimization.py
python src/walk_forward.py
python src/stat_tests.py --samples 2000 --block-size 21
```

输出会生成到 `data/output/`，但不会进入 Git。

Generated outputs are written under `data/output/`, but are excluded from Git.

## 验证 / Verification

```powershell
python -m compileall backend src
python -c "import backend.main; print(backend.main.app.title)"
cd frontend
npm run build
docker compose config
```

## 分支策略 / Branch Strategy

- `main`：稳定分支，默认分支。
- `totoro_develop`：日常开发分支。
- 依赖更新、功能开发和文档调整优先进入 `totoro_develop`，再通过 PR 合并到 `main`。

- `main`: stable default branch.
- `totoro_develop`: daily development branch.
- Dependency updates, features, and documentation changes should land on `totoro_develop` first and then merge into `main` via PR.

## 安全 / Security

本项目会连接第三方 API 和本地数据库。请保护 `.env` 文件，密钥泄露后立即轮换，并按 [SECURITY.md](SECURITY.md) 私下报告安全问题。

This project can connect to third-party APIs and local databases. Keep `.env` files private, rotate exposed keys immediately, and report security issues privately according to [SECURITY.md](SECURITY.md).

## 许可证 / License

MIT License. See [LICENSE](LICENSE).
