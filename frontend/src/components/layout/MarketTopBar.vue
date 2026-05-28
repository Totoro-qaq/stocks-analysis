<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import * as api from '@/api/client'
import { useAppStore } from '@/stores/app'
import type { OverviewData, PortfolioMetric } from '@/types/api'

interface MarketChip {
  label: string
  value: number | null
}

const store = useAppStore()
const overview = ref<OverviewData | null>(null)
const metrics = ref<PortfolioMetric[]>([])
const cumulativeReturns = ref<any[]>([])

onMounted(async () => {
  const [overviewResult, metricsResult, cumulativeResult] = await Promise.allSettled([
    api.getOverview(),
    api.getOptimizedMetrics(),
    api.getCumulativeReturns(),
  ])

  if (overviewResult.status === 'fulfilled') overview.value = overviewResult.value
  if (metricsResult.status === 'fulfilled') metrics.value = metricsResult.value
  if (cumulativeResult.status === 'fulfilled') cumulativeReturns.value = cumulativeResult.value
})

const maxSharpeMetric = computed(() => metrics.value.find(item => item.portfolio === 'max_sharpe') ?? null)

const marketChips = computed<MarketChip[]>(() => {
  const rows = cumulativeReturns.value
  if (rows.length < 2) return []

  const current = rows[rows.length - 1]
  const previous = rows[rows.length - 2]
  return ['QQQ', 'XLK', 'SP500', 'NASDAQ100'].map(label => {
    const currentValue = Number(current[label])
    const previousValue = Number(previous[label])
    if (!Number.isFinite(currentValue) || !Number.isFinite(previousValue)) {
      return { label, value: null }
    }
    return { label, value: (1 + currentValue) / (1 + previousValue) - 1 }
  })
})

const pipelineLabel = computed(() => {
  if (!store.taskStatus) return 'Idle'
  if (store.taskStatus === 'PROGRESS') return store.taskStep || 'Running'
  return store.taskStatus
})

function formatPercent(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '-'
  const sign = value > 0 ? '+' : ''
  return `${sign}${(value * 100).toFixed(digits)}%`
}
</script>

<template>
  <header class="market-topbar">
    <div class="topbar-left">
      <div class="brand-block">
        <span class="brand-title">MarketAnalyzer</span>
        <span class="brand-subtitle">US Tech 50 Quant Terminal</span>
      </div>

      <div class="divider" />

      <div class="market-strip">
        <div v-for="chip in marketChips" :key="chip.label" class="market-chip">
          <span class="chip-label">{{ chip.label }}</span>
          <span class="chip-value" :class="(chip.value ?? 0) >= 0 ? 'positive' : 'negative'">
            {{ formatPercent(chip.value) }}
          </span>
        </div>
      </div>
    </div>

    <div class="topbar-right">
      <div v-if="store.watchlist.length" class="watchlist-strip">
        <span>Watchlist</span>
        <strong>{{ store.watchlist.slice(0, 4).join(' / ') }}</strong>
      </div>
      <div class="meta-item">
        <span>Latest</span>
        <strong>{{ overview?.date_max || '-' }}</strong>
      </div>
      <div class="meta-item">
        <span>Universe</span>
        <strong>{{ overview?.ticker_count ?? '-' }}</strong>
      </div>
      <div class="meta-item">
        <span>Max Sharpe</span>
        <strong :class="(maxSharpeMetric?.annualized_return ?? 0) >= 0 ? 'positive' : 'negative'">
          {{ formatPercent(maxSharpeMetric?.annualized_return) }}
        </strong>
      </div>
      <div class="meta-item">
        <span>Sharpe</span>
        <strong>{{ maxSharpeMetric?.sharpe_ratio?.toFixed(2) ?? '-' }}</strong>
      </div>
      <div class="status-pill" :class="{ running: store.taskStatus === 'PROGRESS', failed: store.taskStatus === 'FAILURE' }">
        {{ pipelineLabel }}
      </div>
    </div>
  </header>
</template>

<style scoped>
.market-topbar {
  min-height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 8px 22px;
  border-bottom: 1px solid var(--tv-border);
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(10px);
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.03);
}

.topbar-left,
.topbar-right,
.market-strip {
  display: flex;
  align-items: center;
}

.topbar-left { gap: 16px; min-width: 0; }
.topbar-right { gap: 10px; flex-shrink: 0; }
.market-strip { gap: 8px; overflow: hidden; }

.brand-block {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
  min-width: 176px;
}

.brand-title {
  color: var(--tv-text-primary);
  font-weight: 800;
  font-size: 14px;
  letter-spacing: 0;
}

.brand-subtitle {
  color: var(--tv-text-muted);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.divider {
  width: 1px;
  height: 26px;
  background: var(--tv-border);
}

.market-chip,
.meta-item {
  border: 1px solid var(--tv-border);
  border-radius: 6px;
  background: var(--tv-bg-secondary);
}

.market-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
}

.chip-label,
.meta-item span {
  color: var(--tv-text-muted);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.chip-value,
.meta-item strong {
  font-family: Consolas, monospace;
  color: var(--tv-text-primary);
  font-size: 12px;
  font-weight: 800;
  line-height: 1;
}

.meta-item {
  min-width: 76px;
  padding: 5px 8px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.watchlist-strip {
  max-width: 240px;
  padding: 5px 9px;
  border: 1px solid var(--tv-border);
  border-radius: 6px;
  background: var(--tv-bg-card);
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.watchlist-strip span {
  color: var(--tv-text-muted);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.watchlist-strip strong {
  overflow: hidden;
  color: var(--tv-text-primary);
  font-family: Consolas, monospace;
  font-size: 12px;
  font-weight: 900;
  line-height: 1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-pill {
  min-width: 72px;
  padding: 7px 10px;
  border-radius: 999px;
  border: 1px solid var(--tv-border);
  color: var(--tv-text-secondary);
  background: var(--tv-bg-secondary);
  font-size: 11px;
  font-weight: 800;
  text-align: center;
  white-space: nowrap;
}

.status-pill.running {
  color: var(--tv-accent-hover);
  border-color: rgba(64, 158, 255, 0.32);
  background: var(--tv-accent-soft);
}

.status-pill.failed {
  color: #c45656;
  border-color: rgba(245, 108, 108, 0.32);
  background: var(--tv-red-bg);
}

.positive { color: var(--tv-green) !important; }
.negative { color: var(--tv-red) !important; }

@media (max-width: 1100px) {
  .market-strip { display: none; }
  .brand-block { min-width: 150px; }
}

@media (max-width: 760px) {
  .market-topbar { align-items: flex-start; flex-direction: column; padding: 10px 14px; }
  .topbar-right { width: 100%; overflow-x: auto; padding-bottom: 2px; }
}
</style>
