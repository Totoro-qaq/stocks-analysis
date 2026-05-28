<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { use } from 'echarts/core'
import { TreemapChart } from 'echarts/charts'
import { TooltipComponent, VisualMapComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import * as api from '@/api/client'

use([TreemapChart, TooltipComponent, VisualMapComponent, CanvasRenderer])

const props = withDefaults(defineProps<{
  height?: string
}>(), {
  height: '420px',
})

interface TreemapLeaf {
  ticker: string
  name: string
  industry: string
  weight: number
  period_return: number | null
  value: [number, number]
}

interface TreemapGroup {
  name: string
  value: number
  children: TreemapLeaf[]
}

interface TreemapResponse {
  groups: TreemapGroup[]
  meta: {
    portfolio: string
    window_days: number
    date_min: string
    date_max: string
  }
}

const treemap = ref<TreemapResponse>({
  groups: [],
  meta: { portfolio: 'max_sharpe', window_days: 60, date_min: '', date_max: '' },
})
const isLoading = ref(false)
const loadError = ref('')
const portfolio = ref('max_sharpe')
const windowDays = ref(60)

async function loadTreemap() {
  isLoading.value = true
  loadError.value = ''
  try {
    treemap.value = await api.getResearchTreemap({
      portfolio: portfolio.value,
      window_days: windowDays.value,
    })
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '热力图数据加载失败'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadTreemap)

function formatPercent(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '-'
  const sign = value > 0 ? '+' : ''
  return `${sign}${(value * 100).toFixed(digits)}%`
}

const chartTitle = computed(() => {
  const portfolioLabel = portfolio.value === 'max_sharpe' ? 'Max Sharpe' : portfolio.value
  return `${portfolioLabel} 权重 / ${windowDays.value}D 收益`
})

const option = computed(() => ({
  tooltip: {
    backgroundColor: 'rgba(17, 24, 39, 0.96)',
    borderColor: 'rgba(17, 24, 39, 0.96)',
    borderWidth: 1,
    padding: [12, 14],
    textStyle: { color: '#f9fafb', fontSize: 12 },
    extraCssText: 'box-shadow: 0 12px 30px rgba(15,23,42,0.22); border-radius: 8px;',
    formatter: (info: any) => {
      const data = info.data
      if (!data?.ticker) {
        return `<div style="font-weight:800;">${info.name}</div>`
      }
      const returnColor = (data.period_return ?? 0) >= 0 ? '#6ee7b7' : '#fca5a5'
      return `
        <div style="font-weight:900; font-size: 14px; margin-bottom: 8px;">${data.ticker}</div>
        <div style="color:#cbd5e1; margin-bottom: 4px;">${data.name ?? ''}</div>
        <div style="display:flex;justify-content:space-between;gap:24px;margin-top:8px;">
          <span style="color:#94a3b8;">Weight</span>
          <strong style="font-family:Consolas,monospace;color:#fff;">${formatPercent(data.weight)}</strong>
        </div>
        <div style="display:flex;justify-content:space-between;gap:24px;margin-top:4px;">
          <span style="color:#94a3b8;">${windowDays.value}D Return</span>
          <strong style="font-family:Consolas,monospace;color:${returnColor};">${formatPercent(data.period_return)}</strong>
        </div>
        <div style="color:#94a3b8;margin-top:8px;">${data.industry}</div>
      `
    },
  },
  visualMap: {
    type: 'continuous',
    dimension: 1,
    min: -0.25,
    max: 0.25,
    orient: 'horizontal',
    right: 0,
    top: -4,
    itemWidth: 150,
    itemHeight: 10,
    text: ['+25%', '-25%'],
    textGap: 8,
    textStyle: { color: 'var(--tv-text-muted)', fontSize: 11, fontFamily: 'Consolas, monospace', fontWeight: 700 },
    inRange: {
      color: ['#be123c', '#f56c6c', '#fca5a5', '#edf2f7', '#86efac', '#10b981', '#047857'],
    },
    show: true,
  },
  series: [
    {
      name: 'US Tech 50 Research Universe',
      type: 'treemap',
      width: '100%',
      height: '100%',
      top: 34,
      bottom: 0,
      roam: false,
      nodeClick: false,
      breadcrumb: { show: false },
      itemStyle: {
        borderColor: '#ffffff',
        borderWidth: 1.5,
        gapWidth: 2,
      },
      label: {
        show: true,
        formatter: (info: any) => {
          const data = info.data
          if (!data?.ticker) return `{group|${info.name}}`
          return `{ticker|${data.ticker}}\n{return|${formatPercent(data.period_return, 1)}}`
        },
        rich: {
          ticker: { fontSize: 14, fontWeight: 900, color: '#ffffff', align: 'center', padding: [0, 0, 4, 0] },
          return: { fontSize: 11, fontWeight: 800, fontFamily: 'Consolas, monospace', color: '#ffffff', align: 'center' },
          group: { fontSize: 12, fontWeight: 900, color: '#111827' },
        },
      },
      upperLabel: {
        show: true,
        height: 24,
        color: '#111827',
        backgroundColor: '#f8fafc',
        fontWeight: 900,
        fontSize: 11,
        padding: [0, 8],
      },
      levels: [
        {
          itemStyle: { borderWidth: 3, borderColor: '#ffffff', gapWidth: 4 },
          upperLabel: { show: false },
        },
        {
          itemStyle: { borderWidth: 2, borderColor: '#ffffff', gapWidth: 2 },
          upperLabel: { show: true },
        },
        {
          itemStyle: { borderWidth: 1.5, borderColor: '#ffffff' },
        },
      ],
      data: treemap.value.groups,
    },
  ],
}))
</script>

<template>
  <div class="treemap-container">
    <div class="treemap-header">
      <div>
        <h3>美股科技 50 研究池热力图</h3>
        <p>SIZE: {{ portfolio === 'max_sharpe' ? 'MAX SHARPE PORTFOLIO WEIGHT' : portfolio.toUpperCase() }} / COLOR: {{ windowDays }}D RETURN / GROUP: INDUSTRY</p>
      </div>
      <div class="controls">
        <select v-model="portfolio" @change="loadTreemap">
          <option value="max_sharpe">Max Sharpe</option>
          <option value="equal_weight">Equal Weight</option>
          <option value="min_variance">Min Variance</option>
          <option value="hrp">HRP</option>
        </select>
        <select v-model.number="windowDays" @change="loadTreemap">
          <option :value="20">20D</option>
          <option :value="60">60D</option>
          <option :value="126">126D</option>
          <option :value="252">252D</option>
        </select>
      </div>
    </div>

    <div class="subheader">
      <span>{{ chartTitle }}</span>
      <span>{{ treemap.meta.date_max || '-' }}</span>
    </div>

    <div class="chart-wrap">
      <v-chart v-if="treemap.groups.length" class="chart" :style="{ height: props.height, minHeight: props.height }" :option="option" autoresize />
      <div v-else class="empty-state" :style="{ height: props.height }">
        {{ isLoading ? '正在加载热力图数据...' : loadError || '暂无热力图数据' }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.treemap-container {
  overflow: hidden;
  border: 1px solid var(--tv-border);
  border-radius: 8px;
  background: var(--tv-bg-card);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.treemap-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 14px 8px;
  border-bottom: 1px solid var(--tv-border);
}

.treemap-header h3 {
  color: var(--tv-text-primary);
  font-size: 15px;
  font-weight: 900;
  letter-spacing: 0.02em;
}

.treemap-header p {
  margin-top: 4px;
  color: var(--tv-text-muted);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.controls {
  display: flex;
  gap: 8px;
}

.controls select {
  height: 30px;
  min-width: 118px;
  border: 1px solid #d9dee8;
  border-radius: 6px;
  background: #f8fafc;
  color: var(--tv-text-primary);
  font-size: 12px;
  font-weight: 800;
  padding: 0 8px;
  outline: none;
}

.subheader {
  display: flex;
  justify-content: space-between;
  padding: 6px 14px 0;
  color: var(--tv-text-muted);
  font-family: Consolas, monospace;
  font-size: 11px;
  font-weight: 800;
}

.chart-wrap {
  padding: 6px 10px 10px;
}

.chart {
  width: 100%;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--tv-text-muted);
  border: 1px dashed var(--tv-border);
  border-radius: 8px;
  background: var(--tv-bg-secondary);
}

@media (max-width: 760px) {
  .treemap-header {
    flex-direction: column;
  }

  .controls {
    width: 100%;
  }

  .controls select {
    flex: 1;
    min-width: 0;
  }
}
</style>
