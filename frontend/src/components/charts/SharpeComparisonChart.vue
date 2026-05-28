<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, GridComponent, LegendComponent, TooltipComponent])

const props = defineProps<{ data: any[]; height?: string }>()

const option = computed(() => {
  if (!props.data?.length) return {}
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const, backgroundColor: 'rgba(255,255,255,0.95)', borderColor: 'var(--tv-border)', textStyle: { color: 'var(--tv-text-primary)', fontSize: 13 }, extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-radius: 8px;' },
    legend: { bottom: 0, padding: [20, 0, 0, 0], textStyle: { color: 'var(--tv-text-secondary)', fontSize: 13 } },
    grid: { left: 55, right: 20, top: 20, bottom: 65 },
    xAxis: { type: 'category' as const, data: props.data.map((d: any) => d.portfolio), axisLabel: { color: 'var(--tv-text-muted)', fontSize: 11 }, axisLine: { lineStyle: { color: 'var(--tv-border)' } } },
    yAxis: { type: 'value' as const, axisLabel: { color: 'var(--tv-text-muted)', fontSize: 11, fontFamily: 'monospace' }, splitLine: { lineStyle: { color: 'var(--tv-border)', type: 'dashed' } } },
    series: [
      { name: '训练期夏普', type: 'bar' as const, data: props.data.map((d: any) => d.avg_train_sharpe), itemStyle: { color: 'var(--tv-accent)', borderRadius: [4,4,0,0] }, barWidth: '35%' },
      { name: '测试期夏普', type: 'bar' as const, data: props.data.map((d: any) => d.avg_test_sharpe), itemStyle: { color: 'var(--tv-green)', borderRadius: [4,4,0,0] }, barWidth: '35%' },
    ],
  }
})
</script>

<template>
  <VChart v-if="data?.length" :option="option" :style="{ height: height || '360px', width: '100%' }" autoresize />
  <div v-else class="text-[var(--tv-text-muted)] text-sm py-12 text-center">暂无数据</div>
</template>