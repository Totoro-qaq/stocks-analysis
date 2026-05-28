<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { HeatmapChart } from 'echarts/charts'
import { TooltipComponent, GridComponent, VisualMapComponent } from 'echarts/components'

use([CanvasRenderer, HeatmapChart, TooltipComponent, GridComponent, VisualMapComponent])

const props = defineProps<{ tickers: string[]; values: number[][]; height?: string }>()

const option = computed(() => {
  if (!props.tickers?.length) return {}
  
  const data = []
  for (let i = 0; i < props.values.length; i++) {
    for (let j = 0; j < props.values[i].length; j++) {
      data.push([j, i, props.values[i][j]])
    }
  }

  return {
    backgroundColor: 'transparent',
    tooltip: { 
      position: 'top',
      backgroundColor: 'rgba(17, 24, 39, 0.96)', 
      borderColor: 'rgba(17, 24, 39, 0.96)', 
      textStyle: { color: '#f9fafb', fontSize: 12 },
      extraCssText: 'box-shadow: 0 12px 30px rgba(15,23,42,0.22); border-radius: 8px;',
      formatter: (params: any) => {
        const xTicker = props.tickers[params.value[0]]
        const yTicker = props.tickers[params.value[1]]
        const corr = Number(params.value[2])
        return `<div style="font-weight:700;margin-bottom:6px;">${yTicker} / ${xTicker}</div>
                <div style="color:#cbd5e1;">Correlation <span style="color:#fff;font-family:monospace;font-weight:700;">${corr.toFixed(3)}</span></div>`
      }
    },
    grid: { top: 72, bottom: 56, left: 82, right: 28, containLabel: false },
    xAxis: { 
      type: 'category', 
      data: props.tickers, 
      position: 'top',
      axisTick: { show: false },
      axisLine: { show: false },
      splitArea: { show: false }, 
      axisLabel: {
        color: '#64748b',
        fontSize: 10,
        interval: props.tickers.length > 36 ? 1 : 0,
        rotate: 55,
        margin: 12,
        fontFamily: 'Consolas, monospace',
      } 
    },
    yAxis: { 
      type: 'category', 
      data: props.tickers, 
      inverse: true,
      axisTick: { show: false },
      axisLine: { show: false },
      splitArea: { show: false },
      axisLabel: {
        color: '#64748b',
        fontSize: 10,
        fontFamily: 'Consolas, monospace',
      }
    },
    visualMap: {
      min: -1,
      max: 1,
      precision: 2,
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      bottom: 14,
      itemWidth: 260,
      itemHeight: 10,
      text: ['+1.00', '-1.00'],
      inRange: {
        color: ['#1d4ed8', '#dbeafe', '#f8fafc', '#fed7aa', '#9f1239']
      },
      textStyle: { color: '#64748b', fontSize: 11, fontFamily: 'Consolas, monospace' }
    },
    series: [{
      name: 'Correlation',
      type: 'heatmap',
      data: data,
      animation: false,
      label: { show: false },
      itemStyle: {
        borderColor: '#ffffff',
        borderWidth: 0.5,
      },
      emphasis: {
        itemStyle: {
          borderColor: '#111827',
          borderWidth: 1.2,
          shadowBlur: 12,
          shadowColor: 'rgba(15, 23, 42, 0.22)'
        }
      }
    }]
  }
})
</script>

<template>
  <div class="heatmap-card">
    <VChart v-if="tickers?.length" :option="option" :style="{ height: height || '600px', width: '100%' }" autoresize />
    <div v-else class="text-[var(--tv-text-muted)] text-sm py-24 text-center">暂无相关性数据</div>
  </div>
</template>

<style scoped>
.heatmap-card {
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #d9dee8;
  background: linear-gradient(180deg, #ffffff 0%, #fbfcfe 100%);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}
</style>
