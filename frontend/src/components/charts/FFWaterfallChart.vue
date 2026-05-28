<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, ScatterChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, TitleComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, ScatterChart, GridComponent, TooltipComponent, TitleComponent])

const props = defineProps<{ data: any; height?: string }>()

const option = computed(() => {
  if (!props.data || Object.keys(props.data).length === 0) return {}

  // Parse factor contributions (handling stringified dict if necessary)
  let factors = props.data.factor_contributions
  if (typeof factors === 'string') {
    try { factors = JSON.parse(factors.replace(/'/g, '"')) } catch(e) {}
  }
  
  if (!factors) return {}

  const factorNames = Object.keys(factors)
  const factorValues = Object.values(factors) as number[]
  
  const alpha = props.data.alpha_contribution || 0
  const total = props.data.total_annualized_return || 0

  // Waterfall Chart Logic
  const categories = ['Total Return', ...factorNames, 'Alpha (Unexplained)']
  const values = [total, ...factorValues, alpha]
  
  // Calculate helper series for waterfall (transparent bottom blocks)
  const baseData = []
  const positiveData = []
  const negativeData = []
  const totalData = []

  let currentSum = 0

  for (let i = 0; i < categories.length; i++) {
    const val = values[i]
    
    if (i === 0) { // Total Return (Full bar)
      baseData.push(0)
      positiveData.push("-")
      negativeData.push("-")
      totalData.push(val)
      currentSum = val
    } else {
      totalData.push("-")
      if (val >= 0) {
        baseData.push(currentSum)
        positiveData.push(val)
        negativeData.push("-")
      } else {
        baseData.push(currentSum + val) // Base drops down
        positiveData.push("-")
        negativeData.push(Math.abs(val))
      }
      currentSum += val
    }
  }

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: 'var(--tv-border)',
      textStyle: { color: 'var(--tv-text-primary)', fontSize: 13 },
      extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-radius: 8px;',
      formatter: function (params: any) {
        let tar = params.find((p: any) => p.seriesName !== 'Base' && p.value !== '-')
        if (!tar) return ''
        const val = tar.seriesName === 'Negative' ? -tar.value : tar.value
        const color = tar.seriesName === 'Total' ? 'var(--tv-accent)' : (val >= 0 ? 'var(--tv-green)' : 'var(--tv-red)')
        const sign = val > 0 ? '+' : ''
        return `<div style="font-weight:700; margin-bottom:4px;">${tar.name}</div>
                <div style="color:var(--tv-text-muted); font-size:12px;">Contribution: 
                  <span style="color:${color}; font-family:monospace; font-weight:600;">${sign}${(val * 100).toFixed(2)}%</span>
                </div>`
      }
    },
    grid: { left: 60, right: 20, top: 30, bottom: 65 },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: { color: 'var(--tv-text-muted)', fontSize: 11, interval: 0, rotate: 30 },
      axisLine: { lineStyle: { color: 'var(--tv-border)' } }
    },
    yAxis: {
      type: 'value',
      axisLabel: { 
        color: 'var(--tv-text-muted)', 
        fontSize: 12, 
        fontFamily: 'monospace',
        formatter: (value: number) => (value * 100).toFixed(0) + '%'
      },
      splitLine: { lineStyle: { color: 'var(--tv-border)', type: 'dashed' } }
    },
    series: [
      {
        name: 'Base',
        type: 'bar',
        stack: 'Total',
        itemStyle: { borderColor: 'transparent', color: 'transparent' },
        emphasis: { itemStyle: { borderColor: 'transparent', color: 'transparent' } },
        data: baseData
      },
      {
        name: 'Total',
        type: 'bar',
        stack: 'Total',
        itemStyle: { color: 'var(--tv-accent)', borderRadius: [4,4,0,0] },
        data: totalData
      },
      {
        name: 'Positive',
        type: 'bar',
        stack: 'Total',
        itemStyle: { color: 'var(--tv-green)', borderRadius: [2,2,0,0] },
        data: positiveData
      },
      {
        name: 'Negative',
        type: 'bar',
        stack: 'Total',
        itemStyle: { color: 'var(--tv-red)', borderRadius: [0,0,2,2] },
        data: negativeData
      }
    ]
  }
})
</script>

<template>
  <VChart v-if="data && Object.keys(data).length" :option="option" :style="{ height: height || '400px', width: '100%' }" autoresize />
  <div v-else class="text-[var(--tv-text-muted)] text-sm py-12 text-center h-full flex items-center justify-center">
    暂无 Fama-French 回归数据。请确保底层流水线已运行。
  </div>
</template>