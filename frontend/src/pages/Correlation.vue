<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import * as api from '@/api/client'
import CorrelationHeatmap from '@/components/charts/CorrelationHeatmap.vue'
import type { CorrelationMatrix } from '@/types/api'

const corrMatrix = ref<CorrelationMatrix>({ tickers: [], values: [] })
const corrWithBench = ref<CorrelationMatrix>({ tickers: [], values: [] })
const isLoading = ref(false)

onMounted(async () => {
  isLoading.value = true
  try {
    const [c, cb] = await Promise.all([api.getCorrelation(false), api.getCorrelation(true)])
    corrMatrix.value = c
    corrWithBench.value = cb
  } finally {
    isLoading.value = false
  }
})

function matrixStats(matrix: CorrelationMatrix) {
  const pairs: { value: number; pair: string }[] = []
  for (let row = 0; row < matrix.values.length; row += 1) {
    for (let col = row + 1; col < matrix.values[row].length; col += 1) {
      const value = Number(matrix.values[row][col])
      if (!Number.isFinite(value)) continue
      pairs.push({ value, pair: `${matrix.tickers[row]} / ${matrix.tickers[col]}` })
    }
  }

  if (!pairs.length) {
    return { avg: null, min: null, max: null, highPairs: 0, maxPair: '-' }
  }

  const avg = pairs.reduce((sum, item) => sum + item.value, 0) / pairs.length
  const maxItem = pairs.reduce((best, item) => item.value > best.value ? item : best, pairs[0])
  const minItem = pairs.reduce((best, item) => item.value < best.value ? item : best, pairs[0])
  return {
    avg,
    min: minItem.value,
    max: maxItem.value,
    highPairs: pairs.filter(item => item.value >= 0.75).length,
    maxPair: maxItem.pair,
  }
}

const stockStats = computed(() => matrixStats(corrMatrix.value))

function formatStat(value: number | null): string {
  return value === null ? '-' : value.toFixed(3)
}
</script>

<template>
  <div class="space-y-6 max-w-[1600px] mx-auto">
    <div class="panel-card p-5 bg-white">
      <div class="flex items-start justify-between gap-6">
        <div>
          <h2 class="text-xl font-bold text-[var(--tv-text-primary)] tracking-tight">相关性矩阵</h2>
          <p class="text-[13px] text-[var(--tv-text-muted)] mt-1">科技股池与主要市场基准的收益相关性视图。</p>
        </div>
        <div v-if="isLoading" class="text-xs text-[var(--tv-text-muted)]">加载数据中...</div>
      </div>

      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-5">
        <div class="stat-box">
          <span>平均相关性</span>
          <strong>{{ formatStat(stockStats.avg) }}</strong>
        </div>
        <div class="stat-box">
          <span>最高相关性</span>
          <strong>{{ formatStat(stockStats.max) }}</strong>
        </div>
        <div class="stat-box">
          <span>最低相关性</span>
          <strong>{{ formatStat(stockStats.min) }}</strong>
        </div>
        <div class="stat-box">
          <span>高相关对数</span>
          <strong>{{ stockStats.highPairs }}</strong>
        </div>
      </div>
      <div class="mt-3 text-xs text-[var(--tv-text-muted)]">
        最高相关组合：<span class="font-mono text-[var(--tv-text-secondary)]">{{ stockStats.maxPair }}</span>
      </div>
    </div>

    <section>
      <div class="section-title">
        <h3>50 股收益率相关性</h3>
        <span>{{ corrMatrix.tickers.length }} assets</span>
      </div>
      <CorrelationHeatmap :tickers="corrMatrix.tickers" :values="corrMatrix.values" height="760px" />
    </section>

    <section v-if="corrWithBench.tickers.length">
      <div class="section-title">
        <h3>含基准相关性</h3>
        <span>{{ corrWithBench.tickers.length }} assets + benchmarks</span>
      </div>
      <CorrelationHeatmap :tickers="corrWithBench.tickers" :values="corrWithBench.values" height="800px" />
    </section>
  </div>
</template>

<style scoped>
.panel-card {
  border-radius: 8px;
  border: 1px solid #d9dee8;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.stat-box {
  border: 1px solid #e5e9f1;
  border-radius: 8px;
  padding: 12px 14px;
  background: #f8fafc;
}

.stat-box span {
  display: block;
  color: var(--tv-text-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.stat-box strong {
  display: block;
  margin-top: 4px;
  color: #111827;
  font-family: Consolas, monospace;
  font-size: 22px;
  line-height: 1.15;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.section-title h3 {
  color: var(--tv-text-primary);
  font-size: 15px;
  font-weight: 700;
}

.section-title span {
  color: var(--tv-text-muted);
  font-family: Consolas, monospace;
  font-size: 12px;
}
</style>
