## 变更内容

<!-- 简要说明本次 PR 改了什么。 -->

## 变更原因

<!-- 说明解决的问题、需求来源或关联 Issue。 -->

## 实现说明

<!-- 说明关键实现、取舍、影响范围；没有特殊实现可写“无”。 -->

## 验证方式

- [ ] `python -m compileall backend src`
- [ ] `python -c "import backend.main; print(backend.main.app.title)"`
- [ ] `cd frontend && npm run build`
- [ ] 如修改部署配置，已执行 `docker compose config`

## 数据与合规检查

- [ ] 未提交 `.env`、密钥、下载行情、ETF 持仓、派生分析输出、报告、日志或演示录屏。
- [ ] 如新增数据源、API 或供应商依赖，已在文档中说明来源和使用边界。
- [ ] 如涉及第三方数据生成结果，确认只保留本地文件，不进入仓库。

## 截图

<!-- UI 变更请附截图；无 UI 变更可写“无”。 -->

## 补充说明

<!-- 风险、后续事项、需要 reviewer 特别关注的点。 -->
