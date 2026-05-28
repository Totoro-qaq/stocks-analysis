<script setup lang="ts">
import { watch, ref, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'

const store = useAppStore()
const visible = ref(false)
let eventSource: EventSource | null = null

watch(() => store.taskId, (id) => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
  
  if (!id) {
    visible.value = false
    return
  }
  
  visible.value = true

  // 使用 Server-Sent Events (SSE) 替换轮询
  eventSource = new EventSource(`/api/pipeline/stream/${id}`)

  eventSource.onmessage = (event) => {
    try {
      const status = JSON.parse(event.data)
      store.updateTask(status.status, status.step, status.progress)
      
      if (status.status === 'SUCCESS' || status.status === 'FAILURE') {
        eventSource?.close()
        eventSource = null
        
        if (status.status === 'SUCCESS') {
          setTimeout(() => { visible.value = false; store.resetTask() }, 2500)
        }
      }
    } catch (e) {
      console.error('Failed to parse SSE event data', e)
    }
  }

  eventSource.onerror = () => {
    console.error('SSE connection error')
    eventSource?.close()
    eventSource = null
  }
})

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
})
</script>

<template>
  <div v-if="visible" class="progress-bar">
    <div class="flex items-center gap-3 max-w-4xl mx-auto">
      <span class="text-xs shrink-0" :class="{
        'text-[var(--tv-accent)]': store.taskStatus === 'PROGRESS',
        'text-[var(--tv-green)]': store.taskStatus === 'SUCCESS',
        'text-[var(--tv-red)]': store.taskStatus === 'FAILURE',
        'text-[var(--tv-text-muted)]': store.taskStatus === 'PENDING',
      }">
        {{ store.taskStatus === 'PENDING' ? '等待' :
           store.taskStatus === 'PROGRESS' ? `${store.taskStep || '计算中...'}` :
           store.taskStatus === 'SUCCESS' ? '完成' :
           store.taskStatus === 'FAILURE' ? '失败' : '' }}
      </span>
      <div class="flex-1 h-1.5 rounded-full overflow-hidden" style="background: var(--tv-bg-hover);">
        <div
          class="h-full rounded-full transition-all duration-700 ease-out"
          :class="store.taskStatus === 'FAILURE' ? 'fail-bar' : 'ok-bar'"
          :style="{ width: `${Math.max(2, (store.taskProgress || 0) * 100)}%` }"
        />
      </div>
      <button
        v-if="store.taskStatus === 'FAILURE' || store.taskStatus === 'SUCCESS'"
        @click="visible = false; store.resetTask()"
        class="text-[10px] text-[var(--tv-text-muted)] hover:text-[var(--tv-text-primary)] transition-colors shrink-0"
      >
        关闭 ✕
      </button>
    </div>
  </div>
</template>

<style scoped>
.progress-bar {
  background: var(--tv-bg-secondary);
  border-bottom: 1px solid var(--tv-border);
  padding: 8px 20px;
}
.ok-bar { background: var(--tv-accent); }
.fail-bar { background: var(--tv-red); }
</style>
