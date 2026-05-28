<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const props = defineProps<{ data: {name: string, value: number}[]; height?: string }>()

const option = computed(() => {
  if (!props.data?.length) return {}
  
  // Sort data by value for better visualization (descending)
  const sortedData = [...props.data].sort((a, b) => a.value - b.value)
  const maxWeight = Math.max(0.1, ...sortedData.map(item => item.value))
  
  return {
    backgroundColor: 'transparent',
    tooltip: { 
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(17,24,39,0.96)', 
      borderColor: 'rgba(17,24,39,0.96)', 
      textStyle: { color: '#f9fafb', fontSize: 12 }, 
      extraCssText: 'box-shadow: 0 12px 30px rgba(15,23,42,0.22); border-radius: 8px;',
      formatter: function (params: any) {
        return `<div style="font-weight:800;margin-bottom:6px;">${params[0].name}</div>
                <div style="color:#cbd5e1;font-size:12px;">Weight <span style="color:#fff;font-family:Consolas,monospace;font-weight:800;">${(params[0].value * 100).toFixed(2)}%</span></div>`
      }
    },
    grid: { left: 60, right: 20, top: 10, bottom: 20 },
    xAxis: { 
      type: 'value', 
      max: Math.min(1, maxWeight * 1.18),
      axisLabel: { 
        color: 'var(--tv-text-muted)',
        fontSize: 10,
        fontFamily: 'Consolas, monospace',
        formatter: (value: number) => `${(value * 100).toFixed(0)}%`
      }, 
      splitLine: { lineStyle: { color: '#eef2f7', type: 'dashed' } } 
    },
    yAxis: { 
      type: 'category', 
      data: sortedData.map(d => d.name),
      axisLabel: { color: 'var(--tv-text-secondary)', fontSize: 11, fontWeight: 600 }, 
      axisLine: { show: false },
      axisTick: { show: false }
    },
    series: [{
      type: 'bar',
      data: sortedData.map(d => d.value),
      barWidth: '60%',
      itemStyle: { 
        color: 'var(--tv-accent)',
        borderRadius: [0, 3, 3, 0]
      },
      showBackground: true,
      backgroundStyle: {
        color: 'var(--tv-bg-secondary)',
        borderRadius: [0, 3, 3, 0]
      }
    }],
  }
})
</script>

<template>
  <VChart v-if="data?.length" :option="option" :style="{ height: height || '360px', width: '100%' }" autoresize />
  <div v-else class="text-[var(--tv-text-muted)] text-sm py-12 text-center">暂无数据</div>
</template>
