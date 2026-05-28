<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as api from '@/api/client'
import StockSelector from '@/components/common/StockSelector.vue'
import StatsGrid from '@/components/cards/StatsGrid.vue'
import BollingerChart from '@/components/charts/BollingerChart.vue'
import DataTable from '@/components/tables/DataTable.vue'
import type { TickerItem, SingleStockMetric } from '@/types/api'

const tickers = ref<TickerItem[]>([])
const selected = ref('')
const metrics = ref<SingleStockMetric[]>([])
const bollinger = ref<any[]>([])

onMounted(async () => {
  tickers.value = await api.getTickers()
  metrics.value = await api.getSingleStockMetrics()
  if (tickers.value.length) selected.value = tickers.value[0].ticker
})

watch(selected, async (t) => { bollinger.value = t ? await api.getBollinger(t) : [] })

const current = () => metrics.value.find(m => m.ticker === selected.value)
const stockMetrics = () => {
  const m = current(); if (!m) return []
  return [
    { label: '年化收益 Ann.Ret', value: m.annualized_return, fmt: 'pct', signal: true },
    { label: '年化波动 Ann.Vol', value: m.annualized_volatility, fmt: 'pct', signal: true },
    { label: '夏普比率 Sharpe', value: m.sharpe_ratio, fmt: '.2f', signal: true },
    { label: '最大回撤 MaxDD', value: m.max_drawdown, fmt: 'pct', signal: true },
  ]
}
</script>

<template>
  <div class="space-y-5">
    <h2 class="text-lg font-semibold text-[var(--tv-text-primary)]">单股分析</h2>

    <div class="flex gap-5">
      <div class="w-64 shrink-0 space-y-3" data-testid="single-stock-controls">
        <StockSelector v-model="selected" :options="tickers" />
        <StatsGrid :metrics="stockMetrics()" />
      </div>
      <div class="flex-1" data-testid="single-stock-chart">
        <BollingerChart :data="bollinger" height="420px" />
      </div>
    </div>

    <div data-testid="single-stock-metrics-table">
      <h3 class="text-sm font-medium text-[var(--tv-text-secondary)] mb-2">全部股票指标</h3>
      <DataTable :data="metrics" :height="'440px'"
        :signal-keys="['annualized_return','annualized_volatility','sharpe_ratio','sortino_ratio','max_drawdown','calmar_ratio','var_95_daily','cvar_95_daily']"
      />
    </div>
  </div>
</template>
