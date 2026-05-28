// API 响应类型定义

export interface OverviewData {
  ticker_count: number
  price_rows: number
  date_min: string
  date_max: string
  failure_count: number
}

export interface TickerInfo {
  selection_rank: number
  ticker: string
  name: string
  sector: string
  industry: string
  weight: number | null
  data_coverage: number | null
  avg_dollar_volume_252: number | null
  selection_score: number | null
}

export interface TickerItem {
  ticker: string
  name: string
}

export interface SingleStockMetric {
  ticker: string
  name: string
  annualized_return: number | null
  annualized_volatility: number | null
  sharpe_ratio: number | null
  sortino_ratio: number | null
  max_drawdown: number | null
  drawdown_coverage: number | null
  max_drawdown_duration_days: number | null
  var_95_daily: number | null
  cvar_95_daily: number | null
  observations: number | null
  beta_gspc: number | null
  beta_ndx: number | null
  beta_qqq: number | null
  beta_xlk: number | null
  corr_vix: number | null
}

export interface PortfolioMetric {
  portfolio: string
  annualized_return: number | null
  annualized_volatility: number | null
  sharpe_ratio: number | null
  sortino_ratio: number | null
  max_drawdown: number | null
  drawdown_coverage: number | null
  calmar_ratio: number | null
  cumulative_return: number | null
  [key: string]: any
}

export interface CorrelationMatrix {
  tickers: string[]
  values: number[][]
}

export interface CumulativeReturn {
  date: string
  [ticker: string]: number | string
}

export interface BollingerBand {
  date: string
  ticker: string
  price: number
  middle_band: number
  upper_band: number
  lower_band: number
  bandwidth: number
  percent_b: number
}

export interface PortfolioWeight {
  ticker: string
  [portfolio: string]: number | string
}

export interface EfficientFrontierPoint {
  target_return: number
  annualized_return: number
  annualized_volatility: number
}

export interface WFSummary {
  portfolio: string
  windows: number
  avg_test_sharpe: number
  avg_train_sharpe: number
  avg_sharpe_decay: number
  worst_test_max_drawdown: number
  win_rate_vs_xlk: number
  win_rate_vs_qqq: number
  [key: string]: any
}

export interface WFWindowMetric {
  window_id: number
  portfolio: string
  test_sharpe_ratio: number
  train_sharpe_ratio: number
  test_start: string
  [key: string]: any
}

export interface SignificanceTest {
  series: string
  test: string
  annualized_return: number | null
  t_stat: number | null
  p_value_one_sided_gt_0: number | null
  sharpe_ratio: number | null
  [key: string]: any
}

export interface BootstrapInterval {
  series: string
  metric: string
  ci_lower: number | null
  ci_upper: number | null
  bootstrap_mean: number | null
}

export interface ExplainedVariance {
  component: string
  explained_variance_ratio: number
  cumulative_ratio: number
}

export interface PCLoading {
  ticker: string
  PC1: number
  PC2: number
  PC3: number
  PC4: number
  PC5: number
}

export interface PCReturn {
  date: string
  [pc: string]: number | string
}

export interface FactorRegression {
  ticker: string
  alpha_annualized: number | null
  alpha_pvalue: number | null
  alpha_significant_5pct: boolean
  r_squared: number
  betas?: Record<string, number>
}

export interface FactorAttribution {
  total_annualized_return: number
  alpha_contribution: number
  factor_contributions: Record<string, number>
  r_squared: number
}

export interface RulesData {
  rules: any[]
  raw: string
}

export interface TaskStatus {
  task_id: string
  status: string
  step?: string
  progress?: number
  error?: string
}

export interface PipelineTimelineStep {
  name: string
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILURE' | string
  started_at: string | null
  finished_at: string | null
  offset_ms: number
  duration_ms: number
  error?: string
}

export interface PipelineTimeline {
  task_id: string | null
  status: 'EMPTY' | 'RUNNING' | 'SUCCESS' | 'FAILURE' | 'UNAVAILABLE' | string
  started_at?: string | null
  finished_at?: string | null
  updated_at?: string | null
  duration_ms?: number
  steps: PipelineTimelineStep[]
  error?: string
}
