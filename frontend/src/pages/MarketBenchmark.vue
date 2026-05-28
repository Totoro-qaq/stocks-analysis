<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as api from '@/api/client'
import CumulativeReturnChart from '@/components/charts/CumulativeReturnChart.vue'

const cumulative = ref<any[]>([])
const vixData = ref<any[]>([])

onMounted(async () => {
  try { cumulative.value = await api.getCumulativeReturns(); vixData.value = await api.getMarket('^VIX') } catch {}
})
</script>

<template>
  <div class="space-y-5">
    <h2 class="text-lg font-semibold text-[var(--tv-text-primary)]">市场与基准</h2>
    <div>
      <h3 class="text-sm font-medium text-[var(--tv-text-secondary)] mb-2">累计收益：等权组合 vs 基准</h3>
      <CumulativeReturnChart :data="cumulative" height="420px" />
    </div>
    <div v-if="vixData.length">
      <h3 class="text-sm font-medium text-[var(--tv-text-secondary)] mb-2">VIX 恐慌指数</h3>
      <CumulativeReturnChart
        :data="vixData.map((d: any) => ({ date: d.date, VIX: d.close }))"
        height="300px"
      />
    </div>
  </div>
</template>
