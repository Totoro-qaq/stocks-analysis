import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
})

// ── 数据 ──
export const getOverview = () => api.get('/data/overview').then(r => r.data)
export const getUniverse = () => api.get('/data/universe').then(r => r.data)
export const getTickers = () => api.get('/data/tickers').then(r => r.data)
export const getMarket = (ticker: string) => api.get('/data/market', { params: { ticker } }).then(r => r.data)
export const getFailures = () => api.get('/data/failures').then(r => r.data)
export const getResearchTreemap = (params = { portfolio: 'max_sharpe', window_days: 60 }) =>
  api.get('/data/treemap', { params }).then(r => r.data)

// ── 分析 ──
export const runAnalysis = () => api.post('/analysis/run').then(r => r.data)
export const getSingleStockMetrics = () => api.get('/analysis/single-stock-metrics').then(r => r.data)
export const getPortfolioMetrics = () => api.get('/analysis/portfolio-metrics').then(r => r.data)
export const getCorrelation = (withBenchmarks = false) =>
  api.get('/analysis/correlation', { params: { with_benchmarks: withBenchmarks } }).then(r => r.data)
export const getCumulativeReturns = () => api.get('/analysis/cumulative-returns').then(r => r.data)
export const getBollinger = (ticker?: string) =>
  api.get('/analysis/bollinger', { params: { ticker } }).then(r => r.data)

// ── 组合优化 ──
export const optimize = (params: any) => api.post('/portfolio/optimize', params).then(r => r.data)
export const getPortfolioWeights = () => api.get('/portfolio/weights').then(r => r.data)
export const getOptimizedMetrics = () => api.get('/portfolio/metrics').then(r => r.data)
export const getEfficientFrontier = () => api.get('/portfolio/efficient-frontier').then(r => r.data)
export const getOptimizedReturns = () => api.get('/portfolio/returns').then(r => r.data)
export const getOptimizedCumulativeReturns = () => api.get('/portfolio/cumulative-returns').then(r => r.data)
export const getHRPDendrogram = () => api.get('/portfolio/hrp-dendrogram').then(r => r.data)

// ── 验证 ──
export const runWalkForward = (params: any) => api.post('/validation/walk-forward', params).then(r => r.data)
export const getWFSummary = () => api.get('/validation/wf-summary').then(r => r.data)
export const getWFWindowMetrics = () => api.get('/validation/wf-window-metrics').then(r => r.data)
export const runStatTests = (params: any) => api.post('/validation/stat-tests', params).then(r => r.data)
export const getSignificanceTests = () => api.get('/validation/significance-tests').then(r => r.data)
export const getBootstrap = () => api.get('/validation/bootstrap').then(r => r.data)

// ── 因子 ──
export const runPCA = (components: number) => api.post('/factor/pca', { components }).then(r => r.data)
export const getExplainedVariance = () => api.get('/factor/explained-variance').then(r => r.data)
export const getLoadings = () => api.get('/factor/loadings').then(r => r.data)
export const getPCReturns = () => api.get('/factor/pc-returns').then(r => r.data)
export const getFFRegression = () => api.get('/factor/ff-regression').then(r => r.data)
export const getFFAttribution = () => api.get('/factor/ff-attribution').then(r => r.data)

// ── 规则 ──
export const getRules = () => api.get('/rules').then(r => r.data)
export const saveRules = (csvContent: string) => api.put('/rules', { csv_content: csvContent }).then(r => r.data)
export const getActiveRules = () => api.get('/rules/active').then(r => r.data)
export const difyExtract = (params: any) => api.post('/rules/dify-extract', params).then(r => r.data)

// ── 报告 ──
export const generateReportStream = (params: any): EventSource => {
  const qs = new URLSearchParams({
    focus: params.focus || 'balanced',
    engine: params.engine || 'deepseek',
    notes: params.notes || '',
  }).toString()
  return new EventSource(`/api/report/generate?${qs}`)
}
export const getCurrentReport = () => api.get('/report/current').then(r => r.data)

// ── 全流程 ──
export const runPipeline = (params: any) => api.post('/pipeline/run', params).then(r => r.data)
export const getPipelineStatus = (taskId: string) =>
  api.get(`/pipeline/status/${taskId}`).then(r => r.data)
export const getPipelineTimeline = () => api.get('/pipeline/timeline').then(r => r.data)
