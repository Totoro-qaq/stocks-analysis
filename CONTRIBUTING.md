# Contributing Guide

Thanks for contributing to Stocks Analysis Platform.

## Local Setup

Backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

Frontend:

```powershell
cd frontend
npm ci
npm run dev
```

## Before Opening a PR

Run the checks that match your change:

```powershell
python -m compileall backend src
python -c "import backend.main; print(backend.main.app.title)"
cd frontend
npm run build
```

## Data Policy

Do not commit downloaded market data, ETF holdings, generated analysis outputs, reports, logs, or demo recordings. See [docs/DATA_NOTICE.md](docs/DATA_NOTICE.md).

## Commit Style

Use Conventional Commits where practical:

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation only
- `refactor:` code restructuring without behavior change
- `test:` tests only
- `ci:` CI/CD configuration
- `chore:` dependency/build/miscellaneous changes

## Pull Requests

Describe:

- What changed.
- Why it changed.
- How it was verified.
- Whether any data generation or provider terms are involved.
