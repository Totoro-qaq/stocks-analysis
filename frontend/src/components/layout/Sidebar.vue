<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import * as api from '@/api/client'

const router = useRouter()
const route = useRoute()
const store = useAppStore()
const isPipelineRunning = computed(() => Boolean(
  store.taskId && ['PENDING', 'STARTED', 'PROGRESS'].includes(store.taskStatus),
))

const pages = [
  { name: 'overview', label: '全局看板', icon: 'OV', path: '/' },
  { name: 'market', label: '市场基准', icon: 'MK', path: '/market' },
  { name: 'singleStock', label: '单股分析', icon: 'ST', path: '/single-stock' },
  { name: 'portfolio', label: '组合优化', icon: 'PF', path: '/portfolio' },
  { name: 'correlation', label: '相关性矩阵', icon: 'CR', path: '/correlation' },
  { name: 'attribution', label: '因子归因', icon: 'FA', path: '/attribution' },
  { name: 'validation', label: '前向验证', icon: 'WF', path: '/validation' },
  { name: 'rules', label: '人工规则', icon: 'RL', path: '/rules' },
  { name: 'report', label: '智能报告', icon: 'RP', path: '/report' },
]

const isActive = (name: string) => route.name === name

async function runFullPipeline() {
  if (store.loading || isPipelineRunning.value) return

  store.loading = true
  try {
    const res = await api.runPipeline({
      max_weight: 0.10, covariance_method: 'sample',
      train_days: 756, test_days: 126, step_days: 126,
    })
    store.setTask(res.task_id)
  } catch (e) { console.error(e) }
  finally { store.loading = false }
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <span class="text-lg font-bold text-[var(--tv-accent)] tracking-tight">MarketAnalyzer</span>
      <span class="text-[10px] text-[var(--tv-text-muted)] block">v2.0 · 美股50股</span>
    </div>

    <nav class="flex-1 py-2 overflow-y-auto">
      <router-link
        v-for="p in pages"
        :key="p.name"
        :to="p.path"
        :data-testid="`nav-${p.name}`"
        class="nav-item"
        :class="{ active: isActive(p.name) }"
      >
        <span class="nav-icon">{{ p.icon }}</span>
        <span class="nav-label">{{ p.label }}</span>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <button
        @click="runFullPipeline"
        :disabled="store.loading || isPipelineRunning"
        data-testid="run-full-pipeline"
        class="run-btn"
      >
        {{ store.loading ? '提交中...' : isPipelineRunning ? '流程执行中...' : '一键全流程' }}
      </button>
      <p class="text-[10px] text-[var(--tv-text-muted)] mt-2 text-center">
        分析 / 优化 / 验证 / 检验 / 报告
      </p>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 220px;
  background: var(--tv-bg-card);
  border-right: 1px solid var(--tv-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  box-shadow: 2px 0 8px rgba(0,0,0,0.02);
  z-index: 10;
}
.sidebar-header {
  padding: 24px 20px 20px;
  border-bottom: 1px solid var(--tv-border);
}
.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  margin: 4px 12px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--tv-text-secondary);
  transition:
    background var(--motion-duration-fast) var(--motion-ease),
    color var(--motion-duration-fast) var(--motion-ease),
    transform var(--motion-duration-fast) var(--motion-ease);
  text-decoration: none;
  overflow: hidden;
}
.nav-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 999px;
  background: var(--tv-accent);
  opacity: 0;
  transform: scaleY(0.45);
  transition:
    opacity var(--motion-duration-fast) var(--motion-ease),
    transform var(--motion-duration-fast) var(--motion-ease);
}
.nav-item:hover {
  background: var(--tv-bg-hover);
  color: var(--tv-text-primary);
  transform: translateX(3px);
}
.nav-item.active {
  background: var(--tv-accent-soft);
  color: var(--tv-accent);
  font-weight: 600;
}
.nav-item.active::before {
  opacity: 1;
  transform: scaleY(1);
}
.nav-icon {
  width: 24px;
  height: 20px;
  border: 1px solid var(--tv-border);
  border-radius: 5px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--tv-text-muted);
  background: var(--tv-bg-secondary);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0;
  flex-shrink: 0;
  transition:
    border-color var(--motion-duration-fast) var(--motion-ease),
    background var(--motion-duration-fast) var(--motion-ease),
    color var(--motion-duration-fast) var(--motion-ease);
}
.nav-item.active .nav-icon {
  border-color: rgba(64, 158, 255, 0.32);
  color: var(--tv-accent);
  background: var(--tv-accent-soft);
}
.nav-label { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sidebar-footer {
  padding: 20px 16px;
  border-top: 1px solid var(--tv-border);
}
.run-btn {
  width: 100%;
  padding: 10px 0;
  background: var(--tv-accent);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition:
    background var(--motion-duration-fast) var(--motion-ease),
    box-shadow var(--motion-duration-fast) var(--motion-ease),
    transform var(--motion-duration-fast) var(--motion-ease);
  box-shadow: 0 2px 4px rgba(64, 158, 255, 0.22);
}
.run-btn:hover:not(:disabled) { background: var(--tv-accent-hover); box-shadow: 0 8px 18px rgba(64, 158, 255, 0.26); transform: translateY(-1px); }
.run-btn:active:not(:disabled) { transform: translateY(0); }
.run-btn:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }
</style>
