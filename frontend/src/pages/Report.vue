<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as api from '@/api/client'
import { useAppStore } from '@/stores/app'
import MarkdownRenderer from '@/components/common/MarkdownRenderer.vue'

const store = useAppStore()
const focus = ref('balanced')
const engine = ref('deepseek')
const notes = ref('')
const reportContent = ref('')
const streaming = ref(false)
let abortController: AbortController | null = null

onMounted(async () => {
  const res = await api.getCurrentReport()
  if (res.has_report) reportContent.value = res.content
})

onUnmounted(() => { if (abortController) abortController.abort() })

async function generateReport() {
  streaming.value = true; reportContent.value = ''
  const qs = new URLSearchParams({ focus: focus.value, engine: engine.value, notes: notes.value }).toString()
  abortController = new AbortController()
  try {
    const response = await fetch(`/api/report/generate?${qs}`, { signal: abortController.signal })
    if (!response.ok) { reportContent.value = `生成失败: HTTP ${response.status}`; return }
    const reader = response.body?.getReader()
    if (!reader) { reportContent.value = '生成失败: 无法读取流'; return }
    const decoder = new TextDecoder('utf-8')
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      reportContent.value += decoder.decode(value, { stream: true })
    }
    reportContent.value += decoder.decode()
  } catch (e: any) {
    if (e.name !== 'AbortError') reportContent.value += `\n\n--- 生成中断: ${e.message || e} ---`
  } finally { streaming.value = false; abortController = null }
}
</script>

<template>
  <div class="h-full flex flex-col max-w-[1400px] mx-auto">
    <div class="mb-6">
      <h2 class="text-xl font-bold text-[var(--tv-text-primary)] tracking-tight">智能投研报告</h2>
      <p class="text-[13px] text-[var(--tv-text-muted)] mt-1">
        利用 DeepSeek 或 Dify 分析全流程数据，生成 Markdown 格式的研究报告。
      </p>
    </div>

    <div class="flex gap-6 flex-1 min-h-0">
      <!-- 左侧控制面板 -->
      <div class="w-80 shrink-0 flex flex-col gap-5">
        <div class="panel-card p-5 bg-white space-y-5 shadow-sm">
          <div>
            <label class="text-[11px] font-semibold text-[var(--tv-text-muted)] uppercase tracking-wider mb-2 block flex items-center gap-1">
              <span>⚙️</span> 生成引擎
            </label>
            <div class="relative">
              <select v-model="engine" data-testid="report-engine" class="tv-select w-full appearance-none">
                <option value="deepseek">DeepSeek (Local)</option>
                <option value="dify">Dify Workflow A (Cloud)</option>
              </select>
              <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-gray-500">▼</div>
            </div>
          </div>

          <div>
            <label class="text-[11px] font-semibold text-[var(--tv-text-muted)] uppercase tracking-wider mb-2 block flex items-center gap-1">
              <span>🎯</span> 报告侧重点
            </label>
            <div class="grid grid-cols-2 gap-2">
              <label v-for="opt in [{v:'balanced',l:'均衡分析'}, {v:'risk_control',l:'风险控制'}, {v:'benchmark_outperformance',l:'跑赢基准'}, {v:'robustness',l:'稳健性'}]" 
                     :key="opt.v" 
                     :data-testid="`report-focus-${opt.v}`"
                     class="cursor-pointer border border-[var(--tv-border)] rounded-md px-3 py-2 text-xs text-center transition-colors hover:bg-gray-50"
                     :class="{'ring-2 ring-[var(--tv-accent)] bg-[var(--tv-accent-soft)] border-[var(--tv-accent)] text-[var(--tv-accent)] font-medium': focus === opt.v}">
                <input type="radio" :value="opt.v" v-model="focus" class="hidden" />
                {{ opt.l }}
              </label>
            </div>
          </div>

          <div>
            <label class="text-[11px] font-semibold text-[var(--tv-text-muted)] uppercase tracking-wider mb-2 block flex items-center gap-1">
              <span>💡</span> 人工投研备注
            </label>
            <textarea v-model="notes" data-testid="report-notes" class="tv-textarea h-32 text-sm leading-relaxed" placeholder="输入你想让 AI 重点关注的结论，例如：'半导体板块波动过大，建议降权'..." />
          </div>
          
          <button @click="generateReport" :disabled="streaming" data-testid="generate-report" class="tv-btn tv-btn-blue w-full py-3 text-sm shadow-md flex justify-center items-center gap-2">
            <span v-if="streaming" class="animate-spin">🌀</span>
            <span v-else>🚀</span>
            {{ streaming ? '正在流式生成...' : '开始生成报告' }}
          </button>
        </div>
      </div>

      <!-- 右侧报告内容 -->
      <div class="flex-1 panel-card bg-white shadow-sm flex flex-col overflow-hidden relative">
        <!-- 装饰性顶部彩条 -->
        <div class="report-accent-bar"></div>
        
        <div class="flex-1 overflow-y-auto p-8 lg:p-12" id="report-container" data-testid="report-content">
          <div v-if="!reportContent && !streaming" class="h-full flex flex-col items-center justify-center text-[var(--tv-text-muted)] opacity-60">
            <span class="text-6xl mb-4">📄</span>
            <p class="text-sm">配置左侧参数并点击生成按钮</p>
          </div>
          
          <div v-else class="prose prose-slate max-w-none text-[14px] leading-relaxed marker:text-[var(--tv-accent)] prose-headings:text-[#111827] prose-a:text-[var(--tv-accent)]">
            <div v-if="streaming && reportContent.length < 10" class="flex items-center gap-3 text-[var(--tv-accent-hover)] font-medium bg-[var(--tv-accent-soft)] p-4 rounded-lg">
              <span class="animate-spin">🌀</span> 正在连接大模型，请稍候...
            </div>
            <MarkdownRenderer :content="reportContent" />
            <span v-if="streaming" class="inline-block w-2 h-4 bg-[var(--tv-text-primary)] ml-1 animate-pulse align-middle"></span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.panel-card { border-radius: 12px; }
.tv-select { background: #f8f9fa; border: 1px solid var(--tv-border); border-radius: 8px; padding: 10px 12px; color: var(--tv-text-primary); font-size: 13px; transition: all 0.2s; }
.tv-select:focus { outline: none; border-color: var(--tv-accent); box-shadow: 0 0 0 3px rgba(41,98,255,0.1); background: #fff; }
.tv-textarea { width: 100%; background: #f8f9fa; border: 1px solid var(--tv-border); border-radius: 8px; padding: 12px; color: var(--tv-text-primary); resize: vertical; transition: all 0.2s; }
.tv-textarea:focus { outline: none; border-color: var(--tv-accent); box-shadow: 0 0 0 3px rgba(41,98,255,0.1); background: #fff; }
.tv-btn { border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.2s; color: #fff; }
.tv-btn-blue { background: var(--tv-accent); }
.tv-btn-blue:hover:not(:disabled) { background: var(--tv-accent-hover); transform: translateY(-1px); }
.tv-btn:disabled { opacity: 0.6; cursor: not-allowed; }

/* 定制滚动条给报告容器 */
.report-accent-bar { height: 4px; width: 100%; background: linear-gradient(90deg, var(--tv-accent), var(--tv-purple), var(--tv-green)); }
#report-container::-webkit-scrollbar { width: 6px; }
#report-container::-webkit-scrollbar-track { background: transparent; }
#report-container::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }
#report-container::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
</style>
