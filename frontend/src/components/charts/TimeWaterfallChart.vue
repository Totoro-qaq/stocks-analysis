<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import type { PipelineTimeline, PipelineTimelineStep } from '@/types/api'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const props = defineProps<{ timeline: PipelineTimeline | null; height?: string }>()

const steps = computed(() => props.timeline?.steps?.filter(step => step.name) ?? [])

const totalDurationMs = computed(() => {
  if (typeof props.timeline?.duration_ms === 'number') return props.timeline.duration_ms
  return steps.value.reduce((maxValue, step) => Math.max(maxValue, (step.offset_ms ?? 0) + (step.duration_ms ?? 0)), 0)
})

const latestTimestamp = computed(() => props.timeline?.finished_at || props.timeline?.updated_at || '')

function formatDuration(ms: number): string {
  if (!Number.isFinite(ms) || ms <= 0) return '0s'
  if (ms < 1000) return `${Math.round(ms)}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  const minutes = Math.floor(ms / 60_000)
  const seconds = Math.round((ms % 60_000) / 1000)
  return `${minutes}m ${seconds}s`
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date)
}

function statusColor(status: string): string {
  if (status === 'SUCCESS') return '#10b981'
  if (status === 'FAILURE') return '#f56c6c'
  if (status === 'RUNNING') return '#409eff'
  return '#cbd5e1'
}

function statusLabel(status: string): string {
  if (status === 'SUCCESS') return '完成'
  if (status === 'FAILURE') return '失败'
  if (status === 'RUNNING') return '执行中'
  return '等待'
}

const option = computed(() => {
  if (!steps.value.length) return {}

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(17,24,39,0.96)',
      borderColor: 'rgba(17,24,39,0.96)',
      textStyle: { color: '#f9fafb', fontSize: 12 },
      extraCssText: 'box-shadow: 0 12px 30px rgba(15,23,42,0.22); border-radius: 8px;',
      formatter: (params: any[]) => {
        const dataIndex = params?.[0]?.dataIndex ?? 0
        const step: PipelineTimelineStep | undefined = steps.value[dataIndex]
        if (!step) return ''
        return `
          <div style="font-weight:900;margin-bottom:6px;">${step.name}</div>
          <div style="display:grid;grid-template-columns:64px 1fr;gap:4px 12px;color:#cbd5e1;">
            <span>Status</span><strong style="color:#fff;">${statusLabel(step.status)}</strong>
            <span>Offset</span><strong style="color:#fff;font-family:Consolas,monospace;">${formatDuration(step.offset_ms ?? 0)}</strong>
            <span>Duration</span><strong style="color:#fff;font-family:Consolas,monospace;">${formatDuration(step.duration_ms ?? 0)}</strong>
            <span>Start</span><strong style="color:#fff;font-family:Consolas,monospace;">${formatTimestamp(step.started_at)}</strong>
          </div>
        `
      },
    },
    grid: { left: 92, right: 18, top: 12, bottom: 28 },
    xAxis: {
      type: 'value',
      min: 0,
      max: Math.max(totalDurationMs.value * 1.08, 1000),
      axisLabel: {
        color: 'var(--tv-text-muted)',
        fontSize: 10,
        fontFamily: 'Consolas, monospace',
        formatter: (value: number) => formatDuration(value),
      },
      axisLine: { lineStyle: { color: 'var(--tv-border)' } },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#eef2f7', type: 'dashed' } },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: steps.value.map(step => step.name),
      axisLabel: {
        color: 'var(--tv-text-secondary)',
        fontSize: 11,
        fontWeight: 800,
        width: 78,
        overflow: 'truncate',
      },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        name: 'offset',
        type: 'bar',
        stack: 'timeline',
        data: steps.value.map(step => Math.max(step.offset_ms ?? 0, 0)),
        itemStyle: { color: 'transparent' },
        emphasis: { disabled: true },
        silent: true,
      },
      {
        name: 'duration',
        type: 'bar',
        stack: 'timeline',
        barWidth: 16,
        data: steps.value.map(step => ({
          value: Math.max(step.duration_ms ?? 0, step.status === 'RUNNING' ? 80 : 4),
          itemStyle: { color: statusColor(step.status), borderRadius: [3, 3, 3, 3] },
        })),
      },
    ],
  }
})
</script>

<template>
  <div v-if="steps.length" class="timeline-shell">
    <div class="timeline-meta">
      <span>Latest run</span>
      <strong>{{ formatDuration(totalDurationMs) }}</strong>
      <em>{{ formatTimestamp(latestTimestamp) }}</em>
    </div>
    <VChart :option="option" :style="{ height: height || '260px', width: '100%' }" autoresize />
  </div>
  <div v-else class="timeline-empty">
    暂无流程耗时数据
  </div>
</template>

<style scoped>
.timeline-shell {
  min-width: 0;
}

.timeline-meta {
  display: grid;
  grid-template-columns: auto auto 1fr;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  color: var(--tv-text-muted);
  font-size: 11px;
  font-weight: 800;
}

.timeline-meta strong {
  color: var(--tv-accent);
  font-family: Consolas, monospace;
  font-size: 12px;
  font-weight: 900;
}

.timeline-meta em {
  overflow: hidden;
  color: var(--tv-text-secondary);
  font-family: Consolas, monospace;
  font-size: 11px;
  font-style: normal;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-empty {
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
</style>
