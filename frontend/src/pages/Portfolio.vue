<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as api from '@/api/client'
import CumulativeReturnChart from '@/components/charts/CumulativeReturnChart.vue'
import DrawdownChart from '@/components/charts/DrawdownChart.vue'
import WeightBarChart from '@/components/charts/WeightBarChart.vue'
import EfficientFrontierChart from '@/components/charts/EfficientFrontierChart.vue'
import DendrogramChart from '@/components/charts/DendrogramChart.vue'
import DataTable from '@/components/tables/DataTable.vue'
import StatsGrid from '@/components/cards/StatsGrid.vue'
import type { PortfolioMetric, PortfolioWeight, EfficientFrontierPoint, CumulativeReturn } from '@/types/api'

const metrics = ref<PortfolioMetric[]>([])
const weights = ref<PortfolioWeight[]>([])
const frontier = ref<EfficientFrontierPoint[]>([])
const cumulative = ref<CumulativeReturn[]>([])
const returns = ref<any[]>([])
const hrpData = ref<any>(null)
const selectedPortfolio = ref('max_sharpe')
const isLoading = ref(false)
const loadError = ref('')

// 优化参数
const objective = ref('max_sharpe')
const covarianceMethod = ref('sample')
const cvarAlpha = ref(0.05)
const isOptimizing = ref(false)

function settledValue<T>(result: PromiseSettledResult<T>, fallback: T): T {
  return result.status === 'fulfilled' ? result.value : fallback
}

function cumulativeFromReturns(rows: any[]): CumulativeReturn[] {
  const running: Record<string, number> = {}

  return rows.map((row) => {
    const next: CumulativeReturn = { date: String(row.date) }
    Object.keys(row)
      .filter((key) => key !== 'date')
      .forEach((key) => {
        const dailyReturn = Number(row[key])
        if (!Number.isFinite(dailyReturn)) return
        running[key] = (1 + (running[key] ?? 0)) * (1 + dailyReturn) - 1
        next[key] = running[key]
      })
    return next
  })
}

function syncSelectedPortfolio() {
  const names = portfolioNames()
  if (!names.length) return
  if (!names.includes(selectedPortfolio.value)) {
    selectedPortfolio.value = names.includes('max_sharpe') ? 'max_sharpe' : names[0]
  }
}

async function loadData() {
  isLoading.value = true
  loadError.value = ''
  try {
    const [m, w, f, c, r, h] = await Promise.allSettled([
      api.getOptimizedMetrics(), api.getPortfolioWeights(), api.getEfficientFrontier(),
      api.getOptimizedCumulativeReturns(), api.getOptimizedReturns(), api.getHRPDendrogram()
    ])

    metrics.value = settledValue(m, [])
    weights.value = settledValue(w, [])
    frontier.value = settledValue(f, [])
    returns.value = settledValue(r, [])
    cumulative.value = settledValue(c, [])
    hrpData.value = settledValue(h, null)

    if (!cumulative.value.length && returns.value.length) {
      cumulative.value = cumulativeFromReturns(returns.value)
    }

    if ([m, w, f, c, r, h].some((result) => result.status === 'rejected')) {
      loadError.value = '部分图表数据未加载，已保留可用结果。'
    }

    syncSelectedPortfolio()
  } finally {
    isLoading.value = false
  }
}

onMounted(loadData)

async function triggerOptimization() {
  isOptimizing.value = true
  try {
    await api.optimize({
      objective: objective.value,
      covariance_method: covarianceMethod.value,
      max_weight: 0.10,
      cvar_alpha: cvarAlpha.value,
      use_black_litterman: false
    })
    setTimeout(loadData, 2000)
  } catch (e) {
    console.error("Optimization failed", e)
  } finally {
    isOptimizing.value = false
  }
}

const portfolioNames = () => weights.value.length ? Object.keys(weights.value[0]).filter(k => k !== 'ticker') : []
const barData = () => weights.value.filter(w => Number(w[selectedPortfolio.value] || 0) > 0.001).map(w => ({ name: w.ticker as string, value: Number(w[selectedPortfolio.value]) || 0 }))

const drawdownData = () => {
  let wealth = 1
  let peak = 1
  return returns.value.map((row: any) => {
    const dailyReturn = Number(row[selectedPortfolio.value] ?? 0)
    if (Number.isFinite(dailyReturn)) {
      wealth *= 1 + dailyReturn
      peak = Math.max(peak, wealth)
    }
    return { date: row.date, return: wealth / peak - 1 }
  })
}

const metricCards = () => {
  const m = metrics.value.find(x => x.portfolio === selectedPortfolio.value)
  if (!m) return []
  return [
    { label: '年化收益 Ann.Ret', value: m.annualized_return, fmt: 'pct', signal: true },
    { label: '年化波动 Ann.Vol', value: m.annualized_volatility, fmt: 'pct', signal: true },
    { label: '夏普比率 Sharpe', value: m.sharpe_ratio, fmt: '.2f', signal: true },
    { label: '最大回撤 MaxDD', value: m.max_drawdown, fmt: 'pct', signal: true },
  ]
}
</script>

<template>
  <div class="space-y-8 max-w-[1400px] mx-auto">
    <div class="flex justify-between items-end">
      <div>
        <h2 class="text-xl font-bold text-[var(--tv-text-primary)] tracking-tight">组合优化模型</h2>
        <p class="text-[13px] text-[var(--tv-text-muted)] mt-1">
          引入 HRP (层次风险平价)、CVaR 尾部风险约束与因子收缩协方差的增强框架。
        </p>
      </div>
      <div v-if="isLoading" class="text-xs text-[var(--tv-text-muted)]">加载数据中...</div>
    </div>

    <div v-if="loadError" class="panel-card px-4 py-3 text-xs text-amber-700 bg-amber-50 border-amber-200">
      {{ loadError }}
    </div>

    <!-- 参数控制面板 (方案 B) -->
    <div class="panel-card p-5 bg-white shadow-sm flex flex-wrap items-end gap-6 border-l-4 border-l-[var(--tv-accent)]">
      <div class="flex-1 min-w-[200px]">
        <label class="text-[11px] font-semibold text-[var(--tv-text-muted)] uppercase tracking-wider mb-2 block">优化目标 (Objective)</label>
        <select v-model="objective" class="tv-select w-full">
          <option value="max_sharpe">马科维茨最大夏普 (Max Sharpe)</option>
          <option value="min_variance">马科维茨最小方差 (Min Variance)</option>
          <option value="min_cvar">CVaR 尾部风险最小化 (Min CVaR)</option>
        </select>
      </div>
      <div class="flex-1 min-w-[200px]">
        <label class="text-[11px] font-semibold text-[var(--tv-text-muted)] uppercase tracking-wider mb-2 block">协方差估计 (Covariance)</label>
        <select v-model="covarianceMethod" class="tv-select w-full">
          <option value="sample">样本协方差 (Sample)</option>
          <option value="ledoit_wolf">Ledoit-Wolf 收缩</option>
          <option value="factor_shrinkage">单因子收缩 (Factor Shrinkage)</option>
        </select>
      </div>
      <div class="flex-1 min-w-[150px]" :class="{'opacity-40 pointer-events-none': objective !== 'min_cvar'}">
        <label class="text-[11px] font-semibold text-[var(--tv-text-muted)] uppercase tracking-wider mb-2 block flex justify-between">
          <span>CVaR 置信度 (α)</span>
          <span class="text-[var(--tv-accent)] font-mono">{{ (cvarAlpha * 100).toFixed(0) }}%</span>
        </label>
        <input type="range" v-model.number="cvarAlpha" min="0.01" max="0.10" step="0.01" class="w-full accent-[var(--tv-accent)] mt-2" />
      </div>
      <div class="w-[140px]">
        <button @click="triggerOptimization" :disabled="isOptimizing" class="tv-btn tv-btn-blue w-full py-2.5 shadow-sm flex justify-center items-center gap-2">
          <span v-if="isOptimizing" class="animate-spin">🌀</span>
          {{ isOptimizing ? '计算中...' : '重新优化' }}
        </button>
      </div>
    </div>

    <!-- 指标卡片 -->
    <StatsGrid :metrics="metricCards()" />

    <!-- HRP 树状图与前沿 -->
    <div class="grid grid-cols-2 gap-6">
      <div class="panel-card p-5 bg-white shadow-sm">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-sm font-semibold text-[var(--tv-text-primary)]">层次聚类树状图 (HRP Dendrogram)</h3>
        </div>
        <DendrogramChart :data="hrpData" height="380px" />
      </div>
      <div class="panel-card p-5 bg-white shadow-sm">
        <h3 class="text-sm font-semibold text-[var(--tv-text-primary)] mb-4">马科维茨有效前沿 (Efficient Frontier)</h3>
        <EfficientFrontierChart :data="frontier" height="380px" />
      </div>
    </div>

    <!-- 收益与回撤对比图 -->
    <div class="grid grid-cols-2 gap-6">
      <div class="panel-card p-5 bg-white shadow-sm">
        <h3 class="text-sm font-semibold text-[var(--tv-text-primary)] mb-4">累计净值对比 (Cumulative Returns)</h3>
        <CumulativeReturnChart :data="cumulative" height="380px" />
      </div>
      <div class="panel-card p-5 bg-white shadow-sm">
        <h3 class="text-sm font-semibold text-[var(--tv-text-primary)] mb-4">回撤深度对比 (Drawdown)</h3>
        <DrawdownChart :data="drawdownData()" height="380px" />
      </div>
    </div>

    <!-- 权重与指标表格 -->
    <div class="grid grid-cols-5 gap-6">
      <div class="col-span-2 panel-card p-5 bg-white shadow-sm flex flex-col">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-sm font-semibold text-[var(--tv-text-primary)]">成分股权重分配</h3>
          <select v-model="selectedPortfolio" class="tv-select text-xs py-1 px-2 min-w-[120px]">
            <option v-for="p in portfolioNames()" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>
        <WeightBarChart :data="barData()" height="340px" class="flex-1" />
      </div>
      <div class="col-span-3 panel-card p-5 bg-white shadow-sm flex flex-col">
        <h3 class="text-sm font-semibold text-[var(--tv-text-primary)] mb-4">组合关键指标 (Metrics)</h3>
        <DataTable :data="metrics" :height="'340px'" class="flex-1"
          :signal-keys="['annualized_return','annualized_volatility','sharpe_ratio','sortino_ratio','max_drawdown','calmar_ratio','cumulative_return']"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.panel-card { border-radius: 12px; }
.tv-select { background: #f8f9fa; border: 1px solid var(--tv-border); border-radius: 8px; padding: 10px 12px; color: var(--tv-text-primary); font-size: 13px; transition: all 0.2s; appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%236b7280'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E"); background-position: right 12px center; background-repeat: no-repeat; background-size: 16px; }
.tv-select:focus { outline: none; border-color: var(--tv-accent); box-shadow: 0 0 0 3px rgba(41,98,255,0.1); background-color: #fff; }
.tv-btn { border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.2s; color: #fff; font-size: 13px; }
.tv-btn-blue { background: var(--tv-accent); }
.tv-btn-blue:hover:not(:disabled) { background: var(--tv-accent-hover); transform: translateY(-1px); }
.tv-btn:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
