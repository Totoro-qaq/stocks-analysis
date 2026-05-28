# 贡献指南 / Contributing Guide

感谢参与美股量化研究平台。

Thanks for contributing to Stocks Analysis Platform.

## 本地环境 / Local Setup

后端 / Backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

前端 / Frontend:

```powershell
cd frontend
npm ci
npm run dev
```

## 分支策略 / Branch Strategy

- `main`：稳定分支，默认分支。
- `totoro_develop`：开发分支，日常修改先进入这里。
- 新功能建议使用 `feat/...`，修复建议使用 `fix/...`。

- `main`: stable default branch.
- `totoro_develop`: development branch for daily changes.
- Use `feat/...` for features and `fix/...` for fixes when practical.

## 提交前检查 / Before Opening a PR

根据改动范围运行：

Run checks that match your change:

```powershell
python -m compileall backend src
python -c "import backend.main; print(backend.main.app.title)"
cd frontend
npm run build
docker compose config
```

## 数据策略 / Data Policy

不要提交下载行情、ETF 持仓、派生分析输出、报告、日志或演示录屏。详见 [docs/DATA_NOTICE.md](docs/DATA_NOTICE.md)。

Do not commit downloaded market data, ETF holdings, generated analysis outputs, reports, logs, or demo recordings. See [docs/DATA_NOTICE.md](docs/DATA_NOTICE.md).

## Commit 规范 / Commit Style

优先使用 Conventional Commits，中文标题可以直接使用：

Prefer Conventional Commits where practical. Chinese commit titles are acceptable.

- `feat:` 新功能 / new feature
- `fix:` 修复 / bug fix
- `docs:` 文档 / documentation only
- `refactor:` 重构 / no behavior change
- `test:` 测试 / tests only
- `ci:` CI/CD
- `chore:` 构建、依赖或杂项 / build, deps, misc

## PR 要求 / Pull Requests

请说明：

Please describe:

- 改了什么 / What changed
- 为什么改 / Why it changed
- 如何验证 / How it was verified
- 是否涉及数据生成、数据源或供应商条款 / Whether data generation, data sources, or provider terms are involved
