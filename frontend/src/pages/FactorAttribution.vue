<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import * as api from '@/api/client'
import FFWaterfallChart from '@/components/charts/FFWaterfallChart.vue'
import DataTable from '@/components/tables/DataTable.vue'

interface ExplainedVarianceRow {
  component: string
  explained_variance_ratio: number
  cumulative_ratio: number
}

interface PCLoadingRow {
  ticker: string
  [component: string]: string | number
}

interface FactorAttributionRow {
  total_annualized_return?: number
  alpha_contribution?: number
  factor_contributions?: Record<string, number> | string
  adj_r_squared?: number
  alpha_pvalue?: number
}

interface FactorRegressionRow extends FactorAttributionRow {
  ticker: string
}

const portfolioAttribution = ref<FactorAttributionRow | null>(null)
const singleStockRegressions = ref<FactorRegressionRow[]>([])
const explainedVariance = ref<ExplainedVarianceRow[]>([])
const pcLoadings = ref<PCLoadingRow[]>([])
const isLoading = ref(false)
const isRunningPca = ref(false)
const loadError = ref('')

function settledValue<T>(result: PromiseSettledResult<T>, fallback: T): T {
  return result.status === 'fulfilled' ? result.value : fallback
}

async function loadFactorData() {
  isLoading.value = true
  loadError.value = ''
  try {
    const [attr, reg, explained, loadings] = await Promise.allSettled([
      api.getFFAttribution(),
      api.getFFRegression(),
      api.getExplainedVariance(),
      api.getLoadings(),
    ])

    const attributionRows = settledValue<FactorAttributionRow[]>(attr, [])
    portfolioAttribution.value = attributionRows.length ? attributionRows[0] : null
    singleStockRegressions.value = settledValue<FactorRegressionRow[]>(reg, [])
    explainedVariance.value = settledValue<ExplainedVarianceRow[]>(explained, [])
    pcLoadings.value = settledValue<PCLoadingRow[]>(loadings, [])

    if ([attr, reg, explained, loadings].some((result) => result.status === 'rejected')) {
      loadError.value = '部分因子数据未加载，已展示可用结果。'
    }
  } finally {
    isLoading.value = false
  }
}

onMounted(loadFactorData)

async function runPcaAndReload() {
  isRunningPca.value = true
  try {
    await api.runPCA(5)
    setTimeout(loadFactorData, 1500)
  } catch (e) {
    loadError.value = 'PCA 计算启动失败。'
  } finally {
    setTimeout(() => { isRunningPca.value = false }, 1500)
  }
}

function parseFactorContributions(value: unknown): Record<string, number> {
  if (!value) return {}
  if (typeof value === 'string') {
    try {
      return JSON.parse(value.replace(/'/g, '"'))
    } catch {
      return {}
    }
  }
  if (typeof value === 'object') return value as Record<string, number>
  return {}
}

const tableData = computed(() => {
  return singleStockRegressions.value.map(row => {
    const factors = parseFactorContributions(row.factor_contributions)
    
    return {
      ticker: row.ticker,
      total_ret: row.total_annualized_return ?? null,
      alpha: row.alpha_contribution ?? null,
      mkt: factors['Mkt-RF'] || 0,
      smb: factors['SMB'] || 0,
      hml: factors['HML'] || 0,
      mom: factors['Mom'] || 0,
      r_squared: row.adj_r_squared ?? null,
      alpha_pvalue: row.alpha_pvalue ?? null
    }
  })
})

const pcaCards = computed(() => {
  const pc1 = explainedVariance.value[0]
  const pc3 = explainedVariance.value[2]
  const last = explainedVariance.value[explainedVariance.value.length - 1]
  const topPc1 = [...pcLoadings.value]
    .sort((a, b) => Math.abs(Number(b.PC1) || 0) - Math.abs(Number(a.PC1) || 0))[0]

  return [
    { label: 'PC1 解释方差', value: pc1?.explained_variance_ratio ?? null },
    { label: '前三因子累计', value: pc3?.cumulative_ratio ?? null },
    { label: '前五因子累计', value: last?.cumulative_ratio ?? null },
    { label: 'PC1 最大载荷', value: topPc1?.ticker ?? '-' },
  ]
})

const pcaLoadingTable = computed(() => {
  return [...pcLoadings.value]
    .map(row => ({
      ticker: row.ticker,
      PC1: Number(row.PC1),
      PC2: Number(row.PC2),
      PC3: Number(row.PC3),
      PC4: Number(row.PC4),
      PC5: Number(row.PC5),
      abs_PC1: Math.abs(Number(row.PC1) || 0),
    }))
    .sort((a, b) => b.abs_PC1 - a.abs_PC1)
})
</script>

<template>
  <div class="space-y-8 max-w-[1400px] mx-auto">
    <div class="flex justify-between items-end">
      <div>
        <h2 class="text-xl font-bold text-[var(--tv-text-primary)] tracking-tight">Fama-French 多因子归因</h2>
        <p class="text-[13px] text-[var(--tv-text-muted)] mt-1">
          展示 PCA 主成分结构，并在 Fama-French 文件可用时拆解 Alpha 与风格因子贡献。
        </p>
      </div>
      <button @click="runPcaAndReload" :disabled="isRunningPca" class="tv-btn">
        {{ isRunningPca ? '计算中...' : '重新计算 PCA' }}
      </button>
    </div>

    <div v-if="loadError" class="panel-card px-4 py-3 text-xs text-amber-700 bg-amber-50 border-amber-200">
      {{ loadError }}
    </div>

    <div class="grid grid-cols-4 gap-5">
      <div v-for="card in pcaCards" :key="card.label" class="panel-card p-5 bg-white shadow-sm flex flex-col justify-center">
        <div class="text-[11px] font-semibold text-[var(--tv-text-muted)] uppercase tracking-wider mb-1">{{ card.label }}</div>
        <div class="text-2xl font-mono font-bold text-[var(--tv-text-primary)]">
          {{ typeof card.value === 'number' ? `${(card.value * 100).toFixed(2)}%` : card.value }}
        </div>
      </div>
    </div>

    <div class="grid grid-cols-4 gap-5" v-if="portfolioAttribution">
      <div class="panel-card p-5 bg-white shadow-sm flex flex-col justify-center">
        <div class="text-[11px] font-semibold text-[var(--tv-text-muted)] uppercase tracking-wider mb-1">Total Return</div>
        <div class="text-2xl font-mono font-bold" :class="(portfolioAttribution.total_annualized_return ?? 0) >= 0 ? 'text-[var(--tv-green)]' : 'text-[var(--tv-red)]'">
          {{ (((portfolioAttribution.total_annualized_return ?? 0) * 100)).toFixed(2) }}%
        </div>
      </div>
      <div class="panel-card p-5 bg-white shadow-sm flex flex-col justify-center">
        <div class="text-[11px] font-semibold text-[var(--tv-text-muted)] uppercase tracking-wider mb-1">Alpha (Unexplained)</div>
        <div class="text-2xl font-mono font-bold" :class="(portfolioAttribution.alpha_contribution ?? 0) >= 0 ? 'text-[var(--tv-accent)]' : 'text-[var(--tv-red)]'">
          {{ (((portfolioAttribution.alpha_contribution ?? 0) * 100)).toFixed(2) }}%
        </div>
      </div>
      <div class="panel-card p-5 bg-white shadow-sm flex flex-col justify-center">
        <div class="text-[11px] font-semibold text-[var(--tv-text-muted)] uppercase tracking-wider mb-1">Alpha P-Value</div>
        <div class="text-2xl font-mono font-bold text-[var(--tv-text-primary)]">
          {{ (portfolioAttribution.alpha_pvalue ?? 0).toFixed(4) }}
          <span class="text-sm ml-1" :class="(portfolioAttribution.alpha_pvalue ?? 1) < 0.05 ? 'text-[var(--tv-green)]' : 'text-[var(--tv-text-muted)]'">
            {{ (portfolioAttribution.alpha_pvalue ?? 1) < 0.05 ? '(Significant)' : '(Not Sig)' }}
          </span>
        </div>
      </div>
      <div class="panel-card p-5 bg-white shadow-sm flex flex-col justify-center">
        <div class="text-[11px] font-semibold text-[var(--tv-text-muted)] uppercase tracking-wider mb-1">Model Adj R²</div>
        <div class="text-2xl font-mono font-bold text-[var(--tv-text-primary)]">
          {{ (((portfolioAttribution.adj_r_squared ?? 0) * 100)).toFixed(1) }}%
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6" v-if="portfolioAttribution">
      <div class="panel-card p-6 bg-white shadow-sm">
        <h3 class="text-base font-semibold text-[var(--tv-text-primary)] mb-6">组合收益归因拆解瀑布图 (Return Decomposition)</h3>
        <FFWaterfallChart :data="portfolioAttribution" height="450px" />
      </div>
    </div>

    <div class="panel-card p-5 bg-white shadow-sm">
      <h3 class="text-base font-semibold text-[var(--tv-text-primary)] mb-4">PCA 因子载荷排序</h3>
      <DataTable 
        :data="pcaLoadingTable" 
        :height="'420px'"
        :pageSize="15"
        :signal-keys="['PC1', 'PC2', 'PC3', 'PC4', 'PC5']"
      />
    </div>

    <div class="panel-card p-5 bg-white shadow-sm">
      <h3 class="text-base font-semibold text-[var(--tv-text-primary)] mb-4">个股因子暴露明细</h3>
      <DataTable 
        :data="tableData" 
        :height="'500px'"
        :pageSize="15"
        :signal-keys="['total_ret', 'alpha', 'mkt', 'smb', 'hml', 'mom']"
      />
    </div>

  </div>
</template>

<style scoped>
.panel-card { border-radius: 12px; border: 1px solid var(--tv-border); }
.tv-btn {
  border: 1px solid var(--tv-border);
  border-radius: 8px;
  padding: 8px 14px;
  background: #fff;
  color: var(--tv-text-primary);
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s;
}
.tv-btn:hover:not(:disabled) {
  border-color: var(--tv-accent);
  color: var(--tv-accent);
}
.tv-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
