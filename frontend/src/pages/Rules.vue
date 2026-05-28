<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as api from '@/api/client'
import DataTable from '@/components/tables/DataTable.vue'

const rulesRaw = ref('')
const rulesDraft = ref('')
const nlInput = ref('')
const startDate = ref(new Date().toISOString().slice(0, 10))
const endDate = ref('')
const activeRules = ref<any[]>([])
const rulesList = ref<any[]>([])

onMounted(async () => { await loadRules() })

async function loadRules() {
  const res = await api.getRules()
  rulesList.value = res.rules || []; rulesRaw.value = res.raw || ''
  const ar = await api.getActiveRules(); activeRules.value = ar || []
}

async function saveRulesHandler() { await api.saveRules(rulesRaw.value); await loadRules() }

async function difyExtractHandler() {
  if (!nlInput.value.trim()) return
  try {
    const res = await api.difyExtract({ human_rule_text: nlInput.value, effective_start_date: startDate.value, effective_end_date: endDate.value })
    rulesDraft.value = res.csv || ''; rulesRaw.value += '\n' + (res.csv || '')
  } catch (e: any) { alert(`Dify 调用失败：${e.message || e}`) }
}

async function recompute() { await saveRulesHandler(); try { await api.runPipeline({ max_weight: 0.10 }) } catch {} }
</script>

<template>
  <div class="space-y-6 max-w-5xl mx-auto">
    <div>
      <h2 class="text-xl font-bold text-[var(--tv-text-primary)] tracking-tight">人工规则干预</h2>
      <p class="text-[13px] text-[var(--tv-text-muted)] mt-1">
        通过自然语言或 CSV 直接编辑覆盖规则，引入 Black-Litterman 贝叶斯先验观点。
      </p>
    </div>

    <!-- Dify AI 提取区 -->
    <details class="panel-card overflow-hidden group" open>
      <summary class="rules-ai-summary text-sm font-semibold text-[var(--tv-text-primary)] cursor-pointer p-4 select-none transition-colors list-none flex justify-between items-center border-b border-transparent group-open:border-[var(--tv-border)]">
        <div class="flex items-center gap-2">
          <span class="rules-ai-icon p-1.5 rounded-md leading-none">✨</span>
          <span>Dify Workflow B：自然语言 → 规则草稿</span>
        </div>
        <span class="rules-ai-toggle transform group-open:rotate-180 transition-transform">▼</span>
      </summary>
      <div class="p-5 space-y-4 bg-white">
        <textarea v-model="nlInput" data-testid="rule-natural-language" placeholder="例如：英伟达近期监管不确定性升高，未来 6 个月最大权重限制到 5%，置信度 80%。" class="tv-textarea h-24 text-sm" />
        <div class="flex gap-4">
          <div class="flex-1">
            <label class="text-[11px] font-semibold text-[var(--tv-text-muted)] uppercase tracking-wider mb-1.5 block">生效开始</label>
            <input type="date" v-model="startDate" class="tv-input w-full" />
          </div>
          <div class="flex-1">
            <label class="text-[11px] font-semibold text-[var(--tv-text-muted)] uppercase tracking-wider mb-1.5 block">生效结束 (可选)</label>
            <input type="date" v-model="endDate" class="tv-input w-full" />
          </div>
        </div>
        <button @click="difyExtractHandler" class="tv-btn tv-btn-purple w-full py-2.5 text-sm shadow-sm hover:shadow-md transition-shadow">
          调用 Dify 抽取模型规则
        </button>
        <div v-if="rulesDraft" class="mt-4">
          <label class="text-[11px] font-semibold text-[var(--tv-text-muted)] uppercase tracking-wider mb-1.5 block">抽取结果 (将自动追加至下方库中)</label>
          <pre class="rules-draft text-[12px] p-4 rounded-lg overflow-auto max-h-40 font-mono shadow-inner">{{ rulesDraft }}</pre>
        </div>
      </div>
    </details>

    <!-- 原生编辑器 -->
    <div class="panel-card p-5 bg-white">
      <div class="flex justify-between items-center mb-3">
        <h3 class="text-sm font-semibold text-[var(--tv-text-primary)] flex items-center gap-2">
          <span class="text-[var(--tv-text-muted)]">📝</span>
          编辑 human_overrides.csv
        </h3>
      </div>
      <textarea v-model="rulesRaw" data-testid="rules-csv-editor" class="tv-textarea h-64 font-mono text-[13px] leading-relaxed bg-[#f8f9fa] border-gray-200 shadow-inner" spellcheck="false" placeholder="ticker,action,return_multiplier,max_weight,bl_confidence,reason" />
      
      <div class="flex justify-between items-center mt-4">
        <div class="text-[12px] text-[var(--tv-text-muted)] font-mono bg-gray-50 px-3 py-1.5 rounded-md border border-gray-200">
          当前解析出 <span class="font-bold text-[var(--tv-accent)]">{{ activeRules.length }}</span> 条有效规则
        </div>
        <div class="flex gap-3">
          <button @click="saveRulesHandler" data-testid="save-rules" class="tv-btn tv-btn-blue px-6 py-2 shadow-sm">保存规则</button>
          <button @click="recompute" class="tv-btn tv-btn-green px-6 py-2 shadow-sm flex items-center gap-1">
            <span>⚡</span> 保存并重算
          </button>
        </div>
      </div>
    </div>

    <!-- 规则列表 -->
    <div v-if="activeRules.length" class="panel-card p-5 bg-white">
      <h3 class="text-sm font-semibold text-[var(--tv-text-primary)] mb-4">当前生效规则清单</h3>
      <DataTable :data="activeRules" :height="'300px'" />
    </div>
  </div>
</template>

<style scoped>
.panel-card { border-radius: 12px; }
.rules-ai-summary { background: linear-gradient(90deg, var(--tv-accent-soft), transparent); }
.rules-ai-summary:hover { background: linear-gradient(90deg, rgba(64, 158, 255, 0.18), transparent); }
.rules-ai-icon { color: var(--tv-accent-hover); background: var(--tv-accent-soft); }
.rules-ai-toggle { color: var(--tv-accent); }
.rules-draft { color: var(--tv-accent-hover); background: var(--tv-accent-soft); border: 1px solid rgba(64, 158, 255, 0.20); }
.tv-textarea { width: 100%; background: var(--tv-bg-primary); border: 1px solid var(--tv-border); border-radius: 8px; padding: 12px 14px; color: var(--tv-text-primary); transition: border-color 0.2s; resize: vertical; }
.tv-textarea:focus { outline: none; border-color: var(--tv-accent); box-shadow: 0 0 0 3px var(--tv-accent-soft); }
.tv-input { width: 100%; background: var(--tv-bg-primary); border: 1px solid var(--tv-border); border-radius: 8px; padding: 9px 12px; color: var(--tv-text-primary); font-size: 13px; transition: all 0.2s; }
.tv-input:focus { outline: none; border-color: var(--tv-accent); box-shadow: 0 0 0 3px var(--tv-accent-soft); }
.tv-btn { border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.2s; color: #fff; }
.tv-btn-blue { background: var(--tv-accent); }
.tv-btn-blue:hover { background: var(--tv-accent-hover); transform: translateY(-1px); }
.tv-btn-green { background: var(--tv-green); }
.tv-btn-green:hover { background: #059669; transform: translateY(-1px); }
.tv-btn-purple { background: linear-gradient(135deg, var(--tv-purple), var(--tv-accent)); }
.tv-btn-purple:hover { background: linear-gradient(135deg, var(--tv-purple-hover), var(--tv-accent-hover)); transform: translateY(-1px); }
</style>
