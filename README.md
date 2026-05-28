# Stocks Analysis Platform

A reproducible US stock quantitative research platform for a 50-stock technology universe. It combines market data ingestion, portfolio analytics, walk-forward validation, statistical testing, human rule overlays, AI-assisted report generation, and a Vue/FastAPI web dashboard.

## Features

- Market data ingestion from Yahoo Finance chart APIs.
- Research universe construction from XLK-related technology equities.
- Single-stock metrics, cumulative returns, Bollinger bands, and correlation matrices.
- Mean-variance portfolio optimization and efficient frontier generation.
- Walk-forward validation with rolling train/test windows.
- Statistical tests and bootstrap confidence intervals.
- Human rule overlays for exclusions, caps, floors, boosts, penalties, and notes.
- FastAPI backend, Celery worker, Redis, MySQL, OpenTelemetry, Jaeger, Prometheus, and Vue frontend.
- Optional DeepSeek-compatible report generation and Dify workflow integration.
- Data-provider-safe repository hygiene: downloaded datasets, generated outputs, and demo recordings are excluded from git.

## Architecture

```text
Market data -> CSV/MySQL -> Analytics -> Portfolio optimization
            -> Walk-forward validation -> Statistical tests
            -> FastAPI/Celery -> Vue dashboard -> Report output
```

## Repository Layout

```text
backend/              FastAPI routers, services, Celery integration
frontend/             Vue 3 + Vite dashboard
src/                  Data ingestion and quantitative analysis scripts
data/                 Local research datasets and generated sample outputs
config/               Environment templates and observability config
docs/                 Design notes, data dictionary, and project plans
scripts/              Demo recording and utility scripts
nginx/                Frontend container nginx config
docker-compose.yml    Full local stack
```

## Requirements

- Python 3.12+ recommended.
- Node.js 20+ or 22+.
- Docker Desktop with Docker Compose for the full stack.

## Configuration

Copy the environment template and fill local secrets:

```powershell
Copy-Item config/.env.example config/.env
```

Important variables:

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

Do not commit `config/.env`.

## Data and Redistribution Notice

Downloaded market data, ETF holdings, generated analytics, local reports, logs, and demo recordings are not committed. See [docs/DATA_NOTICE.md](docs/DATA_NOTICE.md) for the exclusion policy and regeneration commands.

## Local Development

Install backend dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

Install frontend dependencies:

```powershell
cd frontend
npm ci
cd ..
```

Run only the frontend:

```powershell
cd frontend
npm run dev
```

Run the full Docker stack:

```powershell
docker compose up -d --build
```

Default service URLs:

- Frontend: `http://localhost:18080`
- Backend health: `http://localhost:18000/api/health`
- Jaeger: `http://localhost:16686`
- Prometheus: `http://localhost:19090`

## Analysis Scripts

Run from the project root.

```powershell
python src/fetch_market_data.py --summary-only
python src/build_universe_50.py
python src/analysis_engine.py
python src/portfolio_optimization.py
python src/walk_forward.py
python src/stat_tests.py --samples 2000 --block-size 21
```

Generated outputs are written under `data/output/`.

## Verification

Backend syntax and import checks:

```powershell
python -m compileall backend src
python -c "import backend.main; print(backend.main.app.title)"
```

Frontend build:

```powershell
cd frontend
npm run build
```

## Security

This project can connect to third-party APIs and local databases. Keep `.env` files private, rotate exposed API keys immediately, and report security issues privately according to [SECURITY.md](SECURITY.md).

## License

MIT License. See [LICENSE](LICENSE).
