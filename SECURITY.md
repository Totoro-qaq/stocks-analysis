# Security Policy

## Supported Versions

This project is in active development. Security fixes target the latest `main` branch unless a release branch is explicitly announced.

## Reporting a Vulnerability

Do not open a public issue for security vulnerabilities.

Report privately by contacting the maintainer:

- GitHub: `@Totoro-qaq`
- Email: `626836554@qq.com` or `msy626836554@gmail.com`

Please include:

- Affected component and commit SHA.
- Reproduction steps.
- Impact and severity.
- Suggested mitigation, if available.

## Secrets and Data

Never commit:

- `.env` files or API keys.
- Database dumps.
- Downloaded market data or ETF holdings.
- Generated analysis outputs and reports.
- Logs and demo recordings that may include provider-derived data.

See [docs/DATA_NOTICE.md](docs/DATA_NOTICE.md).
