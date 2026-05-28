<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import * as api from '@/api/client'
import MetricCard from '@/components/cards/MetricCard.vue'
import DataTable from '@/components/tables/DataTable.vue'
import HeroAnimation from '@/components/charts/HeroAnimation.vue'
import FinvizTreemap from '@/components/charts/FinvizTreemap.vue'
import TimeWaterfallChart from '@/components/charts/TimeWaterfallChart.vue'
import { useAppStore } from '@/stores/app'
import type { OverviewData, PipelineTimeline, TickerInfo } from '@/types/api'

type FailureRow = Record<string, unknown>

const store = useAppStore()
const overview = ref<OverviewData | null>(null)
const universe = ref<TickerInfo[]>([])
const failures = ref<FailureRow[]>([])
const pipelineTimeline = ref<PipelineTimeline | null>(null)
const isLoading = ref(true)
const loadError = ref('')
const isRecordingDemo = new URLSearchParams(window.location.search).get('recording') === '1'

async function loadPipelineTimeline() {
  try {
    pipelineTimeline.value = await api.getPipelineTimeline()
  } catch (error) {
    console.error('Failed to load pipeline timeline', error)
    pipelineTimeline.value = { task_id: null, status: 'UNAVAILABLE', steps: [] }
  }
}

async function loadOverviewPage() {
  isLoading.value = true
  loadError.value = ''

  const [overviewResult, universeResult, failuresResult, timelineResult] = await Promise.allSettled([
    api.getOverview(),
    api.getUniverse(),
    api.getFailures(),
    api.getPipelineTimeline(),
  ])

  const errors: string[] = []

  if (overviewResult.status === 'fulfilled') {
    overview.value = overviewResult.value
  } else {
    errors.push('总览指标加载失败')
  }

  if (universeResult.status === 'fulfilled') {
    universe.value = universeResult.value
  } else {
    errors.push('研究池明细加载失败')
  }

  if (failuresResult.status === 'fulfilled') {
    failures.value = failuresResult.value
  } else {
    errors.push('异常记录加载失败')
  }

  if (timelineResult.status === 'fulfilled') {
    pipelineTimeline.value = timelineResult.value
  } else {
    errors.push('Pipeline timing load failed')
  }

  loadError.value = errors.join('；')
  isLoading.value = false
}

onMounted(loadOverviewPage)

watch(
  () => [store.taskId, store.taskStatus, store.taskProgress],
  () => {
    if (store.taskId) void loadPipelineTimeline()
  }
)
</script>

<template>
  <div class="overview-page">
    <HeroAnimation v-if="!isRecordingDemo" />

    <div v-if="loadError" class="api-warning">
      {{ loadError }}
    </div>

    <div class="overview-workbench">
      <section class="heatmap-panel" data-testid="research-heatmap">
        <FinvizTreemap height="520px" />
      </section>

      <aside class="side-stack">
        <section class="metrics-grid" aria-label="研究池数据概览">
          <MetricCard v-if="overview" label="研究股票数" :value="overview.ticker_count" fmt=",.0f" :signal="false" />
          <MetricCard v-if="overview" label="行情行数" :value="overview.price_rows" fmt=",.0f" :signal="false" />
          <MetricCard v-if="overview" label="起始日期" :value="overview.date_min" fmt="" :signal="false" />
          <MetricCard v-if="overview" label="结束日期" :value="overview.date_max" fmt="" :signal="false" />
          <div v-if="!overview && isLoading" class="metric-skeleton" v-for="item in 4" :key="item" />
        </section>

        <section class="panel-card compact-card" data-testid="pipeline-waterfall">
          <div class="panel-title">
            <span>Pipeline Timing</span>
            <strong>{{ pipelineTimeline?.status || '-' }}</strong>
          </div>
          <TimeWaterfallChart :timeline="pipelineTimeline" height="250px" />
        </section>

        <section class="panel-card compact-card">
          <div class="panel-title">
            <span>Data Quality</span>
            <strong>{{ failures.length }}</strong>
          </div>
          <DataTable v-if="failures.length" :data="failures" :height="'220px'" />
          <div v-else class="empty-panel">
            {{ isLoading ? '正在检查异常记录...' : '暂无异常记录' }}
          </div>
        </section>
      </aside>
    </div>

    <section class="panel-card research-card">
      <div class="panel-title">
        <span>50 股研究池明细</span>
        <strong>{{ universe.length || '-' }}</strong>
      </div>
      <DataTable v-if="universe.length" :data="universe" :height="'320px'" :pageSize="15" />
      <div v-else class="empty-panel research-empty">
        {{ isLoading ? '正在加载研究池明细...' : '暂无研究池明细数据' }}
      </div>
    </section>
  </div>
</template>

<style scoped>
.overview-page {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.overview-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(320px, 0.8fr);
  gap: 1.5rem;
  align-items: stretch;
}

.heatmap-panel,
.side-stack {
  min-width: 0;
}

.side-stack {
  display: grid;
  gap: 1.25rem;
  align-content: start;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.compact-card,
.research-card {
  padding: 12px;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.panel-title span {
  color: var(--tv-text-primary);
  font-size: 13px;
  font-weight: 900;
}

.panel-title strong {
  min-width: 30px;
  padding: 2px 7px;
  border-radius: 999px;
  color: var(--tv-accent-hover);
  background: var(--tv-accent-soft);
  font-family: Consolas, monospace;
  font-size: 11px;
  font-weight: 900;
  text-align: center;
}

.api-warning {
  padding: 9px 12px;
  border: 1px solid rgba(245, 158, 11, 0.36);
  border-radius: 8px;
  color: #92400e;
  background: #fffbeb;
  font-size: 12px;
  font-weight: 800;
}

.metric-skeleton {
  height: 58px;
  border: 1px solid var(--tv-border);
  border-radius: 6px;
  background: linear-gradient(90deg, #f8fafc 0%, #eef2f7 45%, #f8fafc 90%);
  background-size: 220% 100%;
  animation: skeletonPulse 1.2s ease-in-out infinite;
}

.empty-panel {
  height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--tv-border);
  border-radius: 8px;
  color: var(--tv-text-muted);
  background: var(--tv-bg-secondary);
  font-size: 13px;
  font-weight: 800;
}

.research-empty {
  height: 320px;
}

@keyframes skeletonPulse {
  from { background-position: 120% 0; }
  to { background-position: -120% 0; }
}

@media (max-width: 1100px) {
  .overview-workbench {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
