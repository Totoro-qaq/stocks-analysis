<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { CustomChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'

use([CanvasRenderer, CustomChart, GridComponent, TooltipComponent])

const props = defineProps<{ data: any[]; height?: string }>()

const option = computed(() => {
  if (!props.data?.length) return {}
  
  return {
    backgroundColor: 'transparent',
    tooltip: { 
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(255,255,255,0.95)', 
      borderColor: 'var(--tv-border)', 
      textStyle: { color: 'var(--tv-text-primary)', fontSize: 13 }, 
      extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-radius: 8px;',
      formatter: function (params: any) {
        const item = params[0].data
        return `<div style="font-weight:700;margin-bottom:4px;">${item.date}</div>
                <div style="font-size:12px;color:var(--tv-text-muted);">Price: <span style="color:var(--tv-text-primary);font-family:monospace;">${item.price.toFixed(2)}</span></div>
                <div style="font-size:12px;color:var(--tv-text-muted);">Upper: <span style="color:var(--tv-text-secondary);font-family:monospace;">${item.upper.toFixed(2)}</span></div>
                <div style="font-size:12px;color:var(--tv-text-muted);">Lower: <span style="color:var(--tv-text-secondary);font-family:monospace;">${item.lower.toFixed(2)}</span></div>`
      }
    },
    grid: { left: 55, right: 20, top: 20, bottom: 45 },
    xAxis: { 
      type: 'category', 
      data: props.data.map((d: any) => d.date),
      axisLabel: { color: 'var(--tv-text-muted)', fontSize: 11 }, 
      axisLine: { lineStyle: { color: 'var(--tv-border)' } } 
    },
    yAxis: { 
      type: 'value', 
      scale: true,
      axisLabel: { color: 'var(--tv-text-muted)', fontSize: 11, fontFamily: 'monospace' }, 
      splitLine: { lineStyle: { color: 'var(--tv-border)', type: 'dashed' } } 
    },
    series: [
      {
        name: 'Price & Bollinger',
        type: 'custom',
        renderItem: function (params: any, api: any) {
          const xValue = api.value(0);
          const upperPoint = api.coord([xValue, api.value(3)]);
          const lowerPoint = api.coord([xValue, api.value(4)]);
          const pricePoint = api.coord([xValue, api.value(1)]);
          const isPositive = api.value(1) > api.value(5); // Compare price to MA
          
          return {
            type: 'group',
            children: [
              {
                type: 'line',
                shape: {
                  x1: upperPoint[0], y1: upperPoint[1],
                  x2: lowerPoint[0], y2: lowerPoint[1]
                },
                style: {
                  stroke: 'rgba(64, 158, 255, 0.2)',
                  lineWidth: 1
                }
              },
              {
                type: 'circle',
                shape: { cx: pricePoint[0], cy: pricePoint[1], r: 2 },
                style: {
                  fill: isPositive ? 'var(--tv-green)' : 'var(--tv-red)'
                }
              }
            ]
          };
        },
        data: props.data.map(d => [d.date, d.price, d.ma, d.upper, d.lower, d.ma])
      }
    ],
  }
})
</script>

<template>
  <VChart v-if="data?.length" :option="option" :style="{ height: height || '360px', width: '100%' }" autoresize />
  <div v-else class="text-[var(--tv-text-muted)] text-sm py-12 text-center">暂无布林带数据</div>
</template>
