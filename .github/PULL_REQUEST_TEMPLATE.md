## 变更内容 / What Changed

<!-- 简要说明本次 PR 改了什么。Summarize the change. -->

## 变更原因 / Why

<!-- 说明解决的问题、需求来源或关联 Issue。Explain the reason or linked issue. -->

## 实现说明 / Implementation Notes

<!-- 说明关键实现、取舍、影响范围；没有特殊实现可写“无”。 -->
<!-- Explain key implementation details, trade-offs, and impact. Write "None" if not applicable. -->

## 验证方式 / Verification

- [ ] `python -m compileall backend src`
- [ ] `python -c "import backend.main; print(backend.main.app.title)"`
- [ ] `cd frontend && npm run build`
- [ ] 如修改部署配置，已执行 `docker compose config`
- [ ] If deployment config changed, `docker compose config` was run

## 数据与合规检查 / Data and Compliance Check

- [ ] 未提交 `.env`、密钥、下载行情、ETF 持仓、派生分析输出、报告、日志或演示录屏。
- [ ] No `.env` files, keys, downloaded market data, ETF holdings, generated outputs, reports, logs, or demo recordings are committed.
- [ ] 如新增数据源、API 或供应商依赖，已在文档中说明来源和使用边界。
- [ ] Any new data source, API, or vendor dependency is documented.
- [ ] 如涉及第三方数据生成结果，确认只保留本地文件，不进入仓库。
- [ ] Third-party generated data remains local-only and is not committed.

## 截图 / Screenshots

<!-- UI 变更请附截图；无 UI 变更可写“无”。Attach screenshots for UI changes. -->

## 补充说明 / Notes

<!-- 风险、后续事项、需要 reviewer 特别关注的点。Risks, follow-ups, or review focus. -->
