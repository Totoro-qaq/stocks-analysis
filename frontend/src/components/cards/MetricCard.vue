<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  label: string
  value: number | string | null
  fmt?: string
  signal?: boolean
}>()

const formatted = computed(() => {
  const v = props.value
  if (v === null || v === undefined) return '—'
  if (typeof v === 'string') return v
  const fmt = props.fmt || 'pct'
  if (fmt === 'pct') return `${(v * 100).toFixed(1)}%`
  if (fmt === 'pct2') return `${(v * 100).toFixed(2)}%`
  if (fmt === '.2f') return v.toFixed(2)
  if (fmt === '.4f') return v.toFixed(4)
  if (fmt === ',.0f') return v.toLocaleString()
  return String(v)
})

const colorClass = computed(() => {
  if (!props.signal) return ''
  const v = props.value
  if (typeof v !== 'number' || isNaN(v)) return ''
  if (Math.abs(v) < 0.0001) return ''
  // 回撤/波动率越低越好 — 取反
  const lowerBetter = ['最大回撤', '年化波动率', 'DRW']
  const isLowerBetter = lowerBetter.some(k => props.label.includes(k))
  const positive = isLowerBetter ? v < 0 : v > 0
  return positive ? 'positive' : 'negative'
})
</script>

<template>
  <div class="metric-card" :class="colorClass">
    <div class="metric-label">{{ label }}</div>
    <div class="metric-value" :class="colorClass">
      {{ formatted }}
    </div>
  </div>
</template>

<style scoped>
.metric-card {
  background: var(--tv-bg-card);
  border: 1px solid var(--tv-border);
  border-radius: 6px;
  padding: 10px 14px;
  transition: border-color 0.2s, background 0.2s;
}
.metric-card:hover {
  border-color: var(--tv-border-strong);
  background: var(--tv-bg-secondary);
}
.metric-label {
  font-size: 10px;
  color: var(--tv-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.metric-value {
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
  color: var(--tv-text-primary);
  line-height: 1.2;
}
.metric-value.positive { color: var(--tv-green); }
.metric-value.negative { color: var(--tv-red); }
.metric-card.positive { border-color: rgba(16,185,129,0.32); }
.metric-card.negative { border-color: rgba(245,108,108,0.34); }
</style>
