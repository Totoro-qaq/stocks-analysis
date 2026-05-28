<script setup lang="ts">
import { computed, ref } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, GridComponent, LegendComponent, TooltipComponent])

const COLORS = ['#409eff', '#10b981', '#f56c6c', '#e6a23c', '#8b5cf6', '#14b8a6', '#64748b', '#f472b6']
const RANGE_OPTIONS = ['1M', '3M', '6M', 'YTD', '1Y', 'ALL'] as const

const props = defineProps<{ data: any[]; height?: string }>()
const selectedRange = ref<typeof RANGE_OPTIONS[number]>('ALL')

const filteredData = computed(() => {
  if (!props.data?.length || selectedRange.value === 'ALL') return props.data ?? []

  const latestTime = new Date(props.data[props.data.length - 1].date).getTime()
  if (!Number.isFinite(latestTime)) return props.data

  let startTime = 0
  if (selectedRange.value === 'YTD') {
    const latest = new Date(latestTime)
    startTime = new Date(latest.getFullYear(), 0, 1).getTime()
  } else {
    const rangeDays: Record<string, number> = { '1M': 31, '3M': 92, '6M': 183, '1Y': 365 }
    startTime = latestTime - rangeDays[selectedRange.value] * 24 * 60 * 60 * 1000
  }

  return props.data.filter(row => new Date(row.date).getTime() >= startTime)
})

const option = computed(() => {
  if (!filteredData.value?.length) return {}
  const portfolios = Object.keys(filteredData.value[0]).filter(k => k !== 'date')
  const isPercentSeries = !portfolios.includes('VIX')
  
  return {
    backgroundColor: 'transparent',
    tooltip: { 
      trigger: 'axis', 
      axisPointer: { type: 'cross', label: { backgroundColor: '#111827' } },
      backgroundColor: 'rgba(17,24,39,0.96)', 
      borderColor: 'rgba(17,24,39,0.96)', 
      textStyle: { color: '#f9fafb', fontSize: 12 }, 
      extraCssText: 'box-shadow: 0 12px 30px rgba(15,23,42,0.22); border-radius: 8px;',
      formatter: (params: any[]) => {
        let html = `<div style="font-weight:800;margin-bottom:6px;">${params[0]?.axisValue ?? ''}</div>`
        params.forEach((item) => {
          const value = Number(item.value)
          const formatted = isPercentSeries ? `${(value * 100).toFixed(2)}%` : value.toFixed(2)
          html += `<div style="display:flex;justify-content:space-between;gap:18px;color:#cbd5e1;">
                    <span>${item.marker}${item.seriesName}</span>
                    <strong style="color:#fff;font-family:Consolas,monospace;">${formatted}</strong>
                  </div>`
        })
        return html
      }
    },
    legend: { top: 0, right: 0, itemWidth: 16, itemHeight: 8, textStyle: { color: 'var(--tv-text-secondary)', fontSize: 12, fontWeight: 700 } },
    grid: { left: 58, right: 24, top: 34, bottom: 32 },
    xAxis: { 
      type: 'category', 
      boundaryGap: false,
      data: filteredData.value.map(d => String(d.date).slice(0, 10)), 
      axisLabel: { color: 'var(--tv-text-muted)', fontSize: 11 }, 
      axisLine: { lineStyle: { color: 'var(--tv-border)' } },
      axisTick: { show: false }
    },
    yAxis: { 
      type: 'value', 
      scale: true,
      axisLabel: {
        color: 'var(--tv-text-muted)',
        fontSize: 11,
        fontFamily: 'monospace',
        formatter: (value: number) => isPercentSeries ? `${(value * 100).toFixed(0)}%` : value.toFixed(0)
      }, 
      splitLine: { lineStyle: { color: 'var(--tv-border)', type: 'dashed' } } 
    },
    series: portfolios.map((p, i) => ({
      name: p, 
      type: 'line',
      data: filteredData.value.map(d => d[p]),
      symbol: 'none',
      smooth: true,
      lineStyle: { color: COLORS[i % COLORS.length], width: 2.2 },
      itemStyle: { color: COLORS[i % COLORS.length] },
    })),
  }
})
</script>

<template>
  <div v-if="data?.length" class="chart-shell">
    <div class="range-switch">
      <button
        v-for="range in RANGE_OPTIONS"
        :key="range"
        :class="{ active: selectedRange === range }"
        @click="selectedRange = range"
      >
        {{ range }}
      </button>
    </div>
    <VChart :option="option" :style="{ height: height || '360px', width: '100%' }" autoresize />
  </div>
  <div v-else class="text-[var(--tv-text-muted)] text-sm py-12 text-center">暂无数据</div>
</template>

<style scoped>
.chart-shell {
  position: relative;
}

.range-switch {
  position: absolute;
  z-index: 2;
  top: 0;
  left: 0;
  display: inline-flex;
  height: 26px;
  border: 1px solid #d9dee8;
  border-radius: 6px;
  background: #f8fafc;
  overflow: hidden;
}

.range-switch button {
  min-width: 34px;
  padding: 0 8px;
  border: none;
  border-right: 1px solid #d9dee8;
  color: var(--tv-text-secondary);
  background: transparent;
  font-size: 11px;
  font-weight: 800;
}

.range-switch button:last-child {
  border-right: none;
}

.range-switch button:hover {
  color: var(--tv-text-primary);
  background: #eef2f7;
}

.range-switch button.active {
  color: var(--tv-accent);
  background: #ffffff;
}
</style>
