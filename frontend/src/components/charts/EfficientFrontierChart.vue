<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { ScatterChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, ScatterChart, GridComponent, TooltipComponent])

const props = defineProps<{ data: any[]; height?: string }>()

const option = computed(() => {
  if (!props.data?.length) return {}
  
  return {
    backgroundColor: 'transparent',
    tooltip: { 
      backgroundColor: 'rgba(17,24,39,0.96)', 
      borderColor: 'rgba(17,24,39,0.96)', 
      textStyle: { color: '#f9fafb', fontSize: 12 }, 
      extraCssText: 'box-shadow: 0 12px 30px rgba(15,23,42,0.22); border-radius: 8px;',
      formatter: function (params: any) {
        return `<div style="font-weight:800;margin-bottom:6px;">Efficient Frontier</div>
                <div style="font-size:12px;color:#cbd5e1;">Vol <span style="color:#fff;font-family:Consolas,monospace;font-weight:800;">${(params.value[0]*100).toFixed(2)}%</span></div>
                <div style="font-size:12px;color:#cbd5e1;">Ret <span style="color:#fff;font-family:Consolas,monospace;font-weight:800;">${(params.value[1]*100).toFixed(2)}%</span></div>`
      }
    },
    grid: { left: 55, right: 20, top: 20, bottom: 45 },
    xAxis: { 
      type: 'value', 
      name: 'Volatility',
      nameLocation: 'middle',
      nameGap: 30,
      scale: true,
      axisLabel: { 
        color: 'var(--tv-text-muted)', 
        fontSize: 11,
        fontFamily: 'monospace',
        formatter: (value: number) => (value * 100).toFixed(1) + '%'
      }, 
      axisLine: { lineStyle: { color: 'var(--tv-border)' } },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#eef2f7', type: 'dashed' } }
    },
    yAxis: { 
      type: 'value', 
      name: 'Return',
      nameLocation: 'middle',
      nameGap: 40,
      scale: true,
      axisLabel: { 
        color: 'var(--tv-text-muted)', 
        fontSize: 11, 
        fontFamily: 'monospace',
        formatter: (value: number) => (value * 100).toFixed(1) + '%'
      }, 
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#eef2f7', type: 'dashed' } } 
    },
    series: [{
      type: 'scatter',
      data: props.data.map(d => [d.annualized_volatility, d.annualized_return]),
      symbolSize: 9,
      itemStyle: { 
        color: 'var(--tv-accent)',
        borderColor: '#ffffff',
        borderWidth: 1.5,
        shadowBlur: 8,
        shadowColor: 'rgba(64, 158, 255, 0.24)'
      },
    }],
  }
})
</script>

<template>
  <VChart v-if="data?.length" :option="option" :style="{ height: height || '360px', width: '100%' }" autoresize />
  <div v-else class="text-[var(--tv-text-muted)] text-sm py-12 text-center">暂无数据</div>
</template>
