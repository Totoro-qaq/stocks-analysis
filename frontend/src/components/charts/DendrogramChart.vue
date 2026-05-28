<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { TreeChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'

use([CanvasRenderer, TreeChart, TooltipComponent])

const props = defineProps<{ data: any; height?: string }>()

const option = computed(() => {
  if (!props.data || Object.keys(props.data).length === 0 || props.data.name === "No Data") return {}
  
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: 'var(--tv-border)',
      textStyle: { color: 'var(--tv-text-primary)', fontSize: 12 },
      extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-radius: 8px;',
      formatter: function (info: any) {
        if (!info.value) return info.name;
        return `<div style="font-weight:700; margin-bottom:4px;">${info.name}</div>
                <div style="color:var(--tv-text-muted); font-size:11px;">Distance: <span style="color:var(--tv-accent); font-family:monospace;">${info.value.toFixed(4)}</span></div>`
      }
    },
    series: [
      {
        type: 'tree',
        data: [props.data],
        top: '5%',
        left: '7%',
        bottom: '5%',
        right: '15%',
        symbolSize: 8,
        symbol: 'emptyCircle',
        orient: 'LR',
        itemStyle: {
          color: 'var(--tv-bg-card)',
          borderColor: 'var(--tv-accent)',
          borderWidth: 1.5,
        },
        lineStyle: {
          color: 'var(--tv-border)',
          width: 1.5,
          curveness: 0.5
        },
        label: {
          position: 'left',
          verticalAlign: 'middle',
          align: 'right',
          fontSize: 11,
          fontFamily: 'monospace',
          color: 'var(--tv-text-secondary)'
        },
        leaves: {
          label: {
            position: 'right',
            verticalAlign: 'middle',
            align: 'left',
            fontWeight: 600,
            color: 'var(--tv-text-primary)'
          },
          itemStyle: {
            color: 'var(--tv-accent)',
            borderColor: 'var(--tv-accent)'
          }
        },
        expandAndCollapse: true,
        animationDuration: 550,
        animationDurationUpdate: 750,
        initialTreeDepth: 4
      }
    ]
  }
})
</script>

<template>
  <VChart v-if="data && data.name !== 'No Data'" :option="option" :style="{ height: height || '400px', width: '100%' }" autoresize />
  <div v-else class="text-[var(--tv-text-muted)] text-xs py-12 text-center h-full flex items-center justify-center">
    没有有效的层次聚类数据 (HRP Dendrogram)
  </div>
</template>
