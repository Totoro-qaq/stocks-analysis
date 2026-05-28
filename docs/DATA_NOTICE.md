# Data Notice

This repository intentionally does not include downloaded market data, ETF holdings files, generated analysis CSV/JSON outputs, generated reports, logs, or demo recordings.

## Why Data Is Excluded

The project can fetch or derive data from third-party sources such as Yahoo Finance, State Street SPDR resources, and Sina Finance. Those providers may restrict redistribution, database creation, or public reuse of their data and site content. To keep the public repository low-risk, all provider data and derived research outputs remain local-only.

Excluded paths include:

- `data/raw/*`
- `data/processed/*`
- `data/output/*`
- `sina_crawler/*`
- `frontend/public/demo/*.gif`
- `.recordings/*`
- `logs/*`

Only source code, configuration templates, documentation, and empty directory placeholders are committed.

## Reproducing Outputs

Create a local environment file:

```powershell
Copy-Item config/.env.example config/.env
```

Then regenerate data and outputs locally:

```powershell
python src/fetch_market_data.py --summary-only
python src/build_universe_50.py
python src/analysis_engine.py
python src/portfolio_optimization.py
python src/walk_forward.py
python src/stat_tests.py
```

Before using, publishing, or sharing generated datasets, review and comply with the source providers' current terms.
