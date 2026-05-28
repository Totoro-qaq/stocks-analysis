<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, GridComponent, LegendComponent, TooltipComponent])

const COLORS = ['#409eff', '#10b981', '#f56c6c', '#e6a23c', '#8b5cf6', '#14b8a6', '#64748b', '#f472b6']

const props = defineProps<{ data: any[]; height?: string }>()

const option = computed(() => {
  if (!props.data?.length) return {}
  const portfolios = [...new Set(props.data.map((d: any) => d.portfolio))]
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const, backgroundColor: 'rgba(255,255,255,0.95)', borderColor: 'var(--tv-border)', textStyle: { color: 'var(--tv-text-primary)', fontSize: 13 }, extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-radius: 8px;' },
    legend: { bottom: 0, padding: [20, 0, 0, 0], textStyle: { color: 'var(--tv-text-secondary)', fontSize: 13 } },
    grid: { left: 55, right: 20, top: 20, bottom: 65 },
    xAxis: { type: 'category' as const, data: props.data.filter((d: any) => d.portfolio === portfolios[0]).map((d: any) => `W${d.window_id}`), axisLabel: { color: 'var(--tv-text-muted)', fontSize: 11 }, axisLine: { lineStyle: { color: 'var(--tv-border)' } } },
    yAxis: { type: 'value' as const, axisLabel: { color: 'var(--tv-text-muted)', fontSize: 11, fontFamily: 'monospace' }, splitLine: { lineStyle: { color: 'var(--tv-border)', type: 'dashed' } } },
    series: portfolios.map((p, i) => ({
      name: p as string, type: 'line' as const,
      data: props.data.filter((d: any) => d.portfolio === p).map((d: any) => d.test_sharpe_ratio),
      symbol: 'circle' as const, symbolSize: 6,
      lineStyle: { color: COLORS[i % COLORS.length], width: 2 },
      itemStyle: { color: COLORS[i % COLORS.length] },
    })),
  }
})
</script>

<template>
  <VChart v-if="data?.length" :option="option" :style="{ height: height || '360px', width: '100%' }" autoresize />
  <div v-else class="text-[var(--tv-text-muted)] text-sm py-12 text-center">暂无数据</div>
</template>
