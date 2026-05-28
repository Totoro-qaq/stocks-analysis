<script setup lang="ts">
import MetricCard from './MetricCard.vue'

defineProps<{
  metrics: { label: string; value: number | string | null; fmt?: string; signal?: boolean }[]
}>()
</script>

<template>
  <div class="grid gap-3" style="grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));">
    <MetricCard
      v-for="m in metrics"
      :key="m.label"
      :label="m.label"
      :value="m.value"
      :fmt="m.fmt || 'pct'"
      :signal="m.signal ?? true"
    />
  </div>
</template>
