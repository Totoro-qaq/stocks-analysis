// 表格字段名 → 中英双语标签映射
// 找不到映射的字段保持原名（如 QQQ、XLK、^GSPC、股票 ticker 等）

export const FIELD_LABEL_MAP: Record<string, string> = {
  // ── 股票基础 ──
  ticker: '代码 Ticker',
  name: '名称 Name',
  sector: '行业 Sector',
  industry: '子行业 Industry',
  weight: 'XLK 权重 Weight',

  // ── 股票池筛选 ──
  selection_rank: '排名 Rank',
  selection_score: '综合得分 Score',
  data_coverage: '数据覆盖率 Coverage',
  avg_dollar_volume_252: '日均成交额(252) Avg Volume',
  price_observations: '价格样本数 Obs',
  first_date: '起始日 First Date',
  last_date: '截止日 Last Date',
  selection_reason: '筛选说明 Reason',

  // ── 单股风险收益 ──
  annualized_return: '年化收益率 Ann.Return',
  annualized_volatility: '年化波动率 Ann.Vol',
  sharpe_ratio: '夏普比率 Sharpe',
  sortino_ratio: '索提诺比率 Sortino',
  max_drawdown: '最大回撤 Max DD',
  drawdown_coverage: '回撤占比 DD Coverage',
  max_drawdown_duration_days: '最长回撤(天) DD Duration',
  calmar_ratio: '卡尔玛比率 Calmar',
  var_95_daily: '95% VaR',
  cvar_95_daily: '95% CVaR',
  cumulative_return: '累计收益 Cum.Return',
  observations: '样本数 Obs',

  // ── 因子暴露 ──
  beta_gspc: 'β S&P500',
  beta_ndx: 'β NASDAQ100',
  beta_qqq: 'β QQQ',
  beta_xlk: 'β XLK',
  beta_sp500: 'β S&P500',
  beta_nasdaq100: 'β NASDAQ100',
  corr_vix: 'ρ VIX',

  // ── 跟踪与信息比率 ──
  tracking_error_gspc: '跟踪误差 TE(S&P500)',
  tracking_error_ndx: '跟踪误差 TE(NASDAQ)',
  tracking_error_qqq: '跟踪误差 TE(QQQ)',
  tracking_error_xlk: '跟踪误差 TE(XLK)',
  information_ratio_gspc: '信息比率 IR(S&P500)',
  information_ratio_ndx: '信息比率 IR(NASDAQ)',
  information_ratio_qqq: '信息比率 IR(QQQ)',
  information_ratio_xlk: '信息比率 IR(XLK)',

  // ── t 检验 ──
  mean_return_t_stat: '均值 t 值 Mean t',
  mean_return_p_value: '均值 p 值 Mean p',
  excess_t_stat_gspc: '超额 t(S&P500)',
  excess_p_value_gspc: '超额 p(S&P500)',
  excess_t_stat_ndx: '超额 t(NASDAQ)',
  excess_p_value_ndx: '超额 p(NASDAQ)',
  excess_t_stat_qqq: '超额 t(QQQ)',
  excess_p_value_qqq: '超额 p(QQQ)',
  excess_t_stat_xlk: '超额 t(XLK)',
  excess_p_value_xlk: '超额 p(XLK)',

  // ── 组合 ──
  portfolio: '组合 Portfolio',
  portfolio_names: '组合名称',

  // ── Walk-forward ──
  windows: '窗口数 Windows',
  window_id: '窗口 Window',
  train_start: '训练始 Train Start',
  train_end: '训练止 Train End',
  test_start: '测试始 Test Start',
  test_end: '测试止 Test End',
  test_observations: '测试样本 Test Obs',
  test_cumulative_return: '测试累计收益 Test Cum',
  test_annualized_return: '测试年化收益 Test Ann',
  test_annualized_volatility: '测试年化波动 Test Vol',
  test_sharpe_ratio: '测试夏普 Test Sharpe',
  test_sortino_ratio: '测试索提诺 Test Sortino',
  test_max_drawdown: '测试最大回撤 Test MaxDD',
  test_drawdown_coverage: '测试回撤占比 Test DD%',
  test_calmar_ratio: '测试卡尔玛 Test Calmar',
  test_var_95_daily: '测试95%VaR',
  test_cvar_95_daily: '测试95%CVaR',
  train_annualized_return: '训练年化收益 Train Ann',
  train_annualized_volatility: '训练年化波动 Train Vol',
  train_sharpe_ratio: '训练夏普 Train Sharpe',
  train_max_drawdown: '训练最大回撤 Train MaxDD',
  sharpe_decay: '夏普衰减 Sharpe Decay',
  avg_test_sharpe: '平均测试夏普 Avg Test Sharpe',
  avg_train_sharpe: '平均训练夏普 Avg Train Sharpe',
  avg_sharpe_decay: '平均夏普衰减 Avg Decay',
  median_test_sharpe: '中位测试夏普 Med Sharpe',
  worst_test_max_drawdown: '最差回撤 Worst DD',
  avg_test_drawdown_coverage: '平均回撤占比 Avg DD%',
  avg_test_annualized_return: '平均测试年化收益 Avg Ann',
  median_test_annualized_return: '中位测试年化收益 Med Ann',
  avg_test_annualized_volatility: '平均测试年化波动 Avg Vol',

  // ── 胜率 ──
  win_rate_vs_gspc: '胜率 vs S&P500',
  win_rate_vs_ndx: '胜率 vs NASDAQ',
  win_rate_vs_qqq: '胜率 vs QQQ',
  win_rate_vs_xlk: '胜率 vs XLK',
  beat_gspc: '跑赢S&P500',
  beat_ndx: '跑赢NASDAQ',
  beat_qqq: '跑赢QQQ',
  beat_xlk: '跑赢XLK',
  avg_excess_return_vs_gspc: '超额 vs S&P500',
  avg_excess_return_vs_ndx: '超额 vs NASDAQ',
  avg_excess_return_vs_qqq: '超额 vs QQQ',
  avg_excess_return_vs_xlk: '超额 vs XLK',
  avg_information_ratio_vs_gspc: '信息比率 IR vs S&P500',
  avg_information_ratio_vs_ndx: '信息比率 IR vs NASDAQ',
  avg_information_ratio_vs_qqq: '信息比率 IR vs QQQ',
  avg_information_ratio_vs_xlk: '信息比率 IR vs XLK',

  // ── 统计检验 ──
  series: '序列 Series',
  test: '检验 Test',
  benchmark: '基准 Benchmark',
  mean_daily_return: '日均收益 Mean Daily',
  mean_daily_excess_return: '日均超额 Daily Excess',
  annualized_excess_return: '年化超额 Ann Excess',
  t_stat: 't 统计量',
  p_value_two_sided: 'p 值(双侧)',
  p_value_one_sided_gt_0: 'p 值(单侧>0)',
  excess_sharpe_like: '超额夏普 Excess Sharpe',

  // ── Bootstrap ──
  metric: '指标 Metric',
  bootstrap_samples: 'Bootstrap 次数',
  block_size: '区块大小 Block',
  ci_lower: 'CI 下界',
  ci_upper: 'CI 上界',
  bootstrap_mean: 'Bootstrap 均值',

  // ── PCA ──
  component: '主成分 PC',
  explained_variance_ratio: '解释方差比 Explained%',
  cumulative_ratio: '累计解释比 Cumulative%',

  // ── 因子回归 ──
  alpha_annualized: 'α 年化 Alpha',
  alpha_daily: 'α 日均 Alpha',
  alpha_t_stat: 'α t 值 Alpha t',
  alpha_pvalue: 'α p 值 Alpha p',
  alpha_significant_5pct: 'α 显著(5%)',
  r_squared: 'R²',
  adj_r_squared: 'Adj R²',
  f_statistic: 'F 统计量',
  condition_number: '条件数 Cond',

  // ── 因子归因 ──
  total_annualized_return: '总年化收益 Total',
  alpha_contribution: 'α 贡献 Alpha',
  factor_contributions: '因子贡献 Factors',

  // ── 优化 ──
  covariance_method: '协方差方法 Cov',
  lw_shrinkage: 'LW 收缩强度 Shrinkage',
  target_return: '目标收益 Target',
  equal_weight_return: '等权收益 EW Return',

  // ── 布林带 ──
  date: '日期 Date',
  price: '价格 Price',
  middle_band: '中轨 MA',
  upper_band: '上轨 Upper',
  lower_band: '下轨 Lower',
  bandwidth: '带宽 Bandwidth',
  percent_b: '%B',

  // ── 规则 ──
  action: '动作 Action',
  start_date: '起始日 Start',
  end_date: '截止日 End',
  min_weight: '最低权重 Min',
  max_weight: '最高权重 Max',
  return_multiplier: '收益乘数 Ret×',
  risk_multiplier: '风险乘数 Risk×',
  reason: '理由 Reason',
  source: '来源 Source',
  as_of_date: '截至日 As Of',
  survivorship_note: '生存者偏差备注 Survivorship',
}

/**
 * 获取字段的中英标签；找不到则返回原名。
 * 已保留的原始标识符不翻译：QQQ, XLK, SP500, ^VIX, ^GSPC, ^NDX, ^IRX 等
 */
export function fieldLabel(key: string): string {
  return FIELD_LABEL_MAP[key] ?? key
}

/**
 * 批量翻译对象 keys → labels
 */
export function translateKeys(record: Record<string, any>): Record<string, any> {
  const result: Record<string, any> = {}
  for (const [key, value] of Object.entries(record)) {
    result[fieldLabel(key)] = value
  }
  return result
}

/**
 * 批量翻译对象数组
 */
export function translateRecords(records: Record<string, any>[]): Record<string, any>[] {
  return records.map(translateKeys)
}
