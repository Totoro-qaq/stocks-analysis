<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, GridComponent, LegendComponent, TooltipComponent])

const props = defineProps<{ data: any[]; height?: string }>()

const option = computed(() => {
  if (!props.data?.length) return {}
  
  return {
    backgroundColor: 'transparent',
    tooltip: { 
      trigger: 'axis', 
      backgroundColor: 'rgba(255,255,255,0.95)', 
      borderColor: 'var(--tv-border)', 
      textStyle: { color: 'var(--tv-text-primary)', fontSize: 13 }, 
      extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-radius: 8px;',
      formatter: function (params: any) {
        let res = `<div style="font-weight:700;margin-bottom:4px;">${params[0].name}</div>`
        params.forEach((p: any) => {
          res += `<div style="color:var(--tv-text-muted);font-size:12px;">Drawdown: <span style="color:var(--tv-red);font-family:monospace;font-weight:600;">${(p.value * 100).toFixed(2)}%</span></div>`
        })
        return res
      }
    },
    grid: { left: 55, right: 20, top: 20, bottom: 45 },
    xAxis: { 
      type: 'category', 
      data: props.data.map(d => d.date), 
      axisLabel: { color: 'var(--tv-text-muted)', fontSize: 11 }, 
      axisLine: { lineStyle: { color: 'var(--tv-border)' } } 
    },
    yAxis: { 
      type: 'value', 
      max: 0,
      axisLabel: { 
        color: 'var(--tv-text-muted)', 
        fontSize: 11, 
        fontFamily: 'monospace',
        formatter: (value: number) => (value * 100).toFixed(0) + '%'
      }, 
      splitLine: { lineStyle: { color: 'var(--tv-border)', type: 'dashed' } } 
    },
    series: [{
      name: 'Drawdown', 
      type: 'line',
      data: props.data.map(d => {
        // Calculate running max for drawdown (simplified mock calculation for UI)
        return d.return < 0 ? d.return : 0 
      }),
      symbol: 'none',
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: 'rgba(245, 108, 108, 0.5)' }, { offset: 1, color: 'rgba(245, 108, 108, 0.1)' }]
        }
      },
      lineStyle: { color: '#f56c6c', width: 1.5 },
      itemStyle: { color: '#f56c6c' },
    }],
  }
})
</script>

<template>
  <VChart v-if="data?.length" :option="option" :style="{ height: height || '360px', width: '100%' }" autoresize />
  <div v-else class="text-[var(--tv-text-muted)] text-sm py-12 text-center">暂无数据</div>
</template>
