# 数据字典

## 1. `data/raw/universe_holdings.csv` / `universe_holdings`

含义：

- 当前 State Street 官方 XLK 持仓。
- 用作真实美股科技股研究池的来源。

字段：

- `ticker`：Yahoo Finance 兼容的美股代码。
- `name`：公司或证券名称。
- `sector`：行业板块。
- `industry`：细分行业。
- `weight`：该证券在 XLK 持仓中的权重。
- `source`：股票池来源。
- `as_of_date`：下载日期。
- `survivorship_note`：生存者偏差说明。

重要限制：

- 这是当前 XLK 成分股。
- 回看历史时不是 point-in-time 历史成分股。
- 不能完全排除生存者偏差。

## 2. `data/processed/analysis_universe_50.csv` / `analysis_universe_50`

含义：

- 从 `data/raw/universe_holdings.csv` 中筛选出的 50 支研究股票。

筛选逻辑：

- 当前仍有可用行情。
- 价格数据覆盖率较高。
- 近一年美元成交额流动性较好。
- XLK 持仓权重较高。

字段：

- `selection_rank`：筛选排名。
- `ticker`：股票代码。
- `name`：公司名称。
- `sector`：行业板块。
- `industry`：细分行业。
- `weight`：XLK 持仓权重。
- `first_date`：该股票行情起始日期。
- `last_date`：该股票行情最后日期。
- `price_observations`：价格观测数量。
- `data_coverage`：相对基准交易日的数据覆盖率。
- `avg_dollar_volume_252`：近 252 个交易日平均美元成交额。
- `selection_score`：综合筛选分数。
- `selection_reason`：筛选说明。

## 3. `data/raw/benchmark_metadata.csv` / `benchmark_metadata`

含义：

- 基准指数、ETF 和风险代理变量定义。

包含：

- `^GSPC`：标普500指数。
- `^NDX`：纳斯达克100指数。
- `QQQ`：纳斯达克100可交易 ETF 代理。
- `XLK`：标普500科技板块可交易 ETF 代理。
- `^VIX`：CBOE 恐慌指数。
- `^IRX`：13 周美国国债收益率代理。

字段：

- `code`：内部简称。
- `ticker`：Yahoo Finance ticker。
- `name`：名称。
- `asset_class`：资产类别。
- `proxy_for`：代理含义。
- `source`：数据来源。

## 4. `data/raw/daily_prices.csv` / `daily_prices`

含义：

- Yahoo Finance chart API 获取的日频 OHLCV 行情。

字段：

- `date` / `trade_date`：交易日期。
- `ticker`：股票、ETF、指数、VIX 或利率代码。
- `open`：开盘价。
- `high`：最高价。
- `low`：最低价。
- `close`：收盘价。
- `adj_close`：复权收盘价。
- `volume`：成交量。
- `kind`：CSV 中用于区分 `stock` 或 `benchmark`。
- `source`：数据库中记录的数据来源。

当前默认区间：

- 抓取开始：`2020-01-01`
- 当前实际首个交易日：`2020-01-02`
- 当前数据结束：`2026-05-20`

## 5. `data/raw/data_fetch_failures.csv`

含义：

- 记录行情抓取失败的 ticker 和错误信息。

正常情况下：

- 文件只有表头，没有失败记录。

## 6. `config/human_overrides.csv`

含义：

- 人工研究判断和规则干预输入。
- 用于重新约束组合优化和 walk-forward 验证。

字段：

- `ticker`：股票代码。
- `start_date`：规则生效开始日期。
- `end_date`：规则生效结束日期，空值表示持续生效。
- `action`：规则动作。
- `min_weight`：最小权重。
- `max_weight`：最大权重。
- `return_multiplier`：预期收益乘数。
- `risk_multiplier`：风险乘数。
- `reason`：人工规则原因。

支持动作：

- `exclude`：排除该股票。
- `cap`：限制最大权重。
- `floor`：设置最低权重。
- `boost`：提高预期收益乘数。
- `penalize`：降低预期收益或提高风险惩罚。
- `note`：只进入报告，不改变权重。

## 7. `data/output/` 目录

基础分析输出：

- `single_stock_metrics.csv`：单股风险收益指标。
- `portfolio_metrics.csv`：等权组合指标。
- `correlation_matrix.csv`：50 股相关性矩阵。
- `correlation_matrix_with_benchmarks.csv`：股票与基准相关性矩阵。
- `equal_weight_returns.csv`：等权组合日收益。
- `cumulative_returns.csv`：累计收益曲线。
- `bollinger_bands.csv`：布林带数据。
- `analysis_summary.json`：给 LLM 和 Dify 使用的结构化摘要。

组合优化输出：

- `portfolio_weights.csv`：组合权重。
- `optimized_portfolio_metrics.csv`：优化组合指标。
- `optimized_portfolio_returns.csv`：优化组合日收益。
- `optimized_portfolio_cumulative_returns.csv`：优化组合累计收益。
- `efficient_frontier.csv`：有效前沿数据。
- `active_human_overrides.csv`：当前生效的人工规则。

Walk-forward 输出：

- `walk_forward_summary.csv`：前向验证汇总。
- `walk_forward_window_metrics.csv`：每个测试窗口指标。
- `walk_forward_weights.csv`：每个窗口的组合权重。
- `walk_forward_returns.csv`：每个窗口的测试期收益。

统计检验输出：

- `significance_tests.csv`：t 检验结果。
- `bootstrap_intervals.csv`：bootstrap 置信区间。

报告输出：

- `investment_report.md`：DeepSeek / LangChain 生成的中文报告。

## 8. MySQL 数据库

默认数据库：

- `us_stock_mvp`

主要数据表：

- `universe_holdings`
- `analysis_universe_50`
- `daily_prices`
- `benchmark_metadata`
- `data_fetch_log`

