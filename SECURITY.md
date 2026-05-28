# 安全策略 / Security Policy

## 支持版本 / Supported Versions

项目处于活跃开发阶段。安全修复默认面向最新 `main` 分支，除非另行声明发布分支。

This project is in active development. Security fixes target the latest `main` branch unless a release branch is explicitly announced.

## 漏洞报告 / Reporting a Vulnerability

请不要在公开 Issue 中提交安全漏洞。

Do not open a public issue for security vulnerabilities.

私下联系维护者：

Report privately by contacting the maintainer:

- GitHub: `@Totoro-qaq`
- Email: `626836554@qq.com` or `msy626836554@gmail.com`

请尽量包含：

Please include:

- 受影响组件和 commit SHA / affected component and commit SHA
- 复现步骤 / reproduction steps
- 影响范围和严重程度 / impact and severity
- 建议修复方向（可选）/ suggested mitigation, if available

## 密钥与数据 / Secrets and Data

不要提交：

Never commit:

- `.env` 文件或 API Key / `.env` files or API keys
- 数据库 dump / database dumps
- 下载行情或 ETF 持仓 / downloaded market data or ETF holdings
- 派生分析输出和报告 / generated analysis outputs and reports
- 可能包含供应商数据的日志或演示录屏 / logs and demo recordings that may include provider-derived data

详见 [docs/DATA_NOTICE.md](docs/DATA_NOTICE.md)。

See [docs/DATA_NOTICE.md](docs/DATA_NOTICE.md).
