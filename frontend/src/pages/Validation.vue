<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as api from '@/api/client'
import SharpeComparisonChart from '@/components/charts/SharpeComparisonChart.vue'
import WindowSharpeLine from '@/components/charts/WindowSharpeLine.vue'
import DataTable from '@/components/tables/DataTable.vue'
import type { WFSummary, WFWindowMetric, SignificanceTest, BootstrapInterval } from '@/types/api'

const wfSummary = ref<WFSummary[]>([])
const wfMetrics = ref<WFWindowMetric[]>([])
const tests = ref<SignificanceTest[]>([])
const bootstrap = ref<BootstrapInterval[]>([])

onMounted(async () => {
  const [ws, wm, t, b] = await Promise.all([
    api.getWFSummary(), api.getWFWindowMetrics(), api.getSignificanceTests(), api.getBootstrap(),
  ])
  wfSummary.value = ws; wfMetrics.value = wm; tests.value = t; bootstrap.value = b
})
</script>

<template>
  <div class="space-y-5">
    <h2 class="text-lg font-semibold text-[var(--tv-text-primary)]">Walk-forward 与统计检验</h2>

    <div>
      <h3 class="text-sm font-medium text-[var(--tv-text-secondary)] mb-2">样本外汇总</h3>
      <DataTable :data="wfSummary" :height="'200px'"
        :signal-keys="['avg_test_sharpe','avg_train_sharpe','avg_sharpe_decay','worst_test_max_drawdown']"
      />
    </div>

    <div class="grid grid-cols-2 gap-4">
      <SharpeComparisonChart :data="wfSummary" height="360px" />
      <WindowSharpeLine :data="wfMetrics" height="360px" />
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div>
        <h3 class="text-sm font-medium text-[var(--tv-text-secondary)] mb-2">统计显著性</h3>
        <DataTable :data="tests" :height="'360px'"
          :signal-keys="['annualized_return','sharpe_ratio','t_stat','excess_sharpe_like']"
        />
      </div>
      <div>
        <h3 class="text-sm font-medium text-[var(--tv-text-secondary)] mb-2">Bootstrap 区间</h3>
        <DataTable :data="bootstrap" :height="'360px'" />
      </div>
    </div>
  </div>
</template>
