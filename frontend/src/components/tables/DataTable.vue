<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { fieldLabel } from '@/types/fieldLabels'
import { useAppStore } from '@/stores/app'

const props = defineProps<{
  data: any[]
  columns?: { key: string; label: string }[]
  height?: string
  signalKeys?: string[]
  pageSize?: number // 0 means no pagination
}>()

const store = useAppStore()
const sortKey = ref<string | null>(null)
const sortDir = ref<'asc' | 'desc'>('asc')
const hiddenCols = ref<Set<string>>(new Set())
const showColMenu = ref(false)
const currentPage = ref(1)
const searchQuery = ref('')
const quickFilter = ref<'all' | 'positive' | 'negative'>('all')

function toggleColMenu() { showColMenu.value = !showColMenu.value }
function toggleCol(key: string) {
  const s = new Set(hiddenCols.value)
  s.has(key) ? s.delete(key) : s.add(key)
  hiddenCols.value = s
}

const computedCols = computed(() => {
  let keys: string[]
  if (props.columns) {
    keys = props.columns.map(c => c.key)
  } else if (props.data.length) {
    keys = Object.keys(props.data[0])
  } else {
    return []
  }
  return keys.map(k => ({
    key: k,
    label: props.columns?.find(c => c.key === k)?.label ?? fieldLabel(k),
  }))
})

const visibleCols = computed(() => computedCols.value.filter(c => !hiddenCols.value.has(c.key)))

const filteredData = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  return props.data.filter(row => {
    const matchesQuery = !query || Object.values(row).some(value => String(value ?? '').toLowerCase().includes(query))
    if (!matchesQuery) return false

    if (quickFilter.value === 'all') return true
    return Object.keys(row).some(key => {
      if (!isSignalKey(key)) return false
      const value = row[key]
      if (typeof value !== 'number' || isNaN(value) || Math.abs(value) < 0.0001) return false
      return quickFilter.value === 'positive'
        ? isPositiveSignal(key, value)
        : !isPositiveSignal(key, value)
    })
  })
})

function sortedData() {
  let res = filteredData.value
  if (sortKey.value && res.length) {
    res = [...res].sort((a, b) => {
      const va = a[sortKey.value!] ?? 0
      const vb = b[sortKey.value!] ?? 0
      const cmp = va < vb ? -1 : va > vb ? 1 : 0
      return sortDir.value === 'asc' ? cmp : -cmp
    })
  }
  return res
}

const paginatedData = computed(() => {
  const allData = sortedData()
  if (!props.pageSize || props.pageSize <= 0) return allData
  const start = (currentPage.value - 1) * props.pageSize
  return allData.slice(start, start + props.pageSize)
})

const totalPages = computed(() => {
  if (!props.pageSize || props.pageSize <= 0) return 1
  return Math.max(1, Math.ceil(filteredData.value.length / props.pageSize))
})

watch([searchQuery, quickFilter, () => props.data.length], () => {
  currentPage.value = 1
})

function setPage(p: number) {
  if (p >= 1 && p <= totalPages.value) {
    currentPage.value = p
  }
}

function toggleSort(key: string) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
  currentPage.value = 1 // Reset to first page on sort
}

const defaultSignalKeys = new Set([
  'annualized_return', 'annualized_volatility', 'sharpe_ratio', 'sortino_ratio',
  'max_drawdown', 'calmar_ratio', 'var_95_daily', 'cvar_95_daily',
  'cumulative_return', 'alpha_annualized', 'alpha_daily',
  'avg_test_sharpe', 'avg_train_sharpe', 'test_sharpe_ratio', 'train_sharpe_ratio',
  'sharpe_decay', 'avg_sharpe_decay', 'median_test_sharpe',
  'excess_sharpe_like', 'information_ratio', 'avg_information_ratio',
  'mean_daily_return', 'mean_daily_excess_return', 'annualized_excess_return',
  'excess_return', 'alpha_contribution', 'total_annualized_return',
  'tracking_error', 'annualized_return',
])

function isSignalKey(key: string): boolean {
  if (props.signalKeys?.includes(key)) return true
  return defaultSignalKeys.has(key)
}

function isPositiveSignal(key: string, val: any): boolean {
  if (typeof val !== 'number' || isNaN(val)) return false
  const lowerIsBetter = new Set([
    'max_drawdown', 'annualized_volatility', 'var_95_daily', 'cvar_95_daily',
    'tracking_error', 'sharpe_decay', 'avg_sharpe_decay', 'drawdown_coverage',
  ])
  if (lowerIsBetter.has(key)) return val < 0
  return val > 0
}

function signalClass(key: string, val: any): string {
  if (!isSignalKey(key)) return ''
  if (typeof val !== 'number' || isNaN(val)) return ''
  if (Math.abs(val) < 0.0001) return ''
  return isPositiveSignal(key, val) ? 'positive' : 'negative'
}

function formatCell(val: any, colKey: string): string {
  if (val === undefined || val === null) return '-'
  if (typeof val === 'boolean') return val ? 'Yes' : 'No'

  if (typeof val === 'number') {
    if (Number.isInteger(val) && Math.abs(val) < 1000000) return val.toLocaleString()
    const abs = Math.abs(val)
    if (abs >= 100) return val.toFixed(1)
    if (abs >= 1) return val.toFixed(2)
    if (abs >= 0.01) return val.toFixed(4)
    if (abs === 0) return '0'
    return val.toExponential(2)
  }
  return String(val)
}

function isNumberCol(key: string): boolean {
  if (!props.data.length) return false
  return typeof props.data[0][key] === 'number'
}

function tooltip(key: string): string | null {
  const label = fieldLabel(key)
  if (label !== key) return `${key}\n${label}`
  return null
}

function isTickerColumn(key: string): boolean {
  return key === 'ticker'
}
</script>

<template>
  <div
    class="tv-table-container"
    :style="{ height: height || '420px' }"
  >
    <!-- 工具栏 -->
    <div class="screener-toolbar">
      <div class="toolbar-left">
        <span class="table-kicker">Screener</span>
        <span class="table-count">
          {{ filteredData.length }} / {{ data.length }} rows · {{ visibleCols.length }} columns
        </span>
      </div>

      <div class="toolbar-actions">
        <input
          v-model="searchQuery"
          class="search-input"
          placeholder="Search ticker, metric..."
          type="search"
        />
        <div class="segmented">
          <button :class="{ active: quickFilter === 'all' }" @click="quickFilter = 'all'">All</button>
          <button :class="{ active: quickFilter === 'positive' }" @click="quickFilter = 'positive'">Positive</button>
          <button :class="{ active: quickFilter === 'negative' }" @click="quickFilter = 'negative'">Risk</button>
        </div>
        <div class="relative">
        <button
          @click="toggleColMenu"
          class="columns-btn"     
        >
          Columns
        </button>
        <div
          v-if="showColMenu"
          class="absolute right-0 top-full mt-1 z-50 bg-[var(--tv-bg-card)] border border-[var(--tv-border)] rounded-lg shadow-xl p-2 min-w-[200px] max-h-[320px] overflow-y-auto"
        >
          <label
            v-for="col in computedCols"
            :key="col.key"
            class="flex items-center gap-2 px-3 py-2 rounded text-[12px] cursor-pointer hover:bg-[var(--tv-bg-hover)]"
          >
            <input
              type="checkbox"
              :checked="!hiddenCols.has(col.key)"
              @change="toggleCol(col.key)"
              class="accent-[var(--tv-accent)] w-3.5 h-3.5"
            />
            <span class="text-[var(--tv-text-primary)] truncate">{{ col.label }}</span>
          </label>
        </div>
      </div>
      </div>
    </div>

    <!-- 表格本体 -->
    <div class="overflow-auto flex-1 bg-[var(--tv-bg-card)] relative">
      <table class="w-full text-[13px] border-collapse">
        <thead class="sticky top-0 z-10 bg-[var(--tv-bg-card)] shadow-sm">
          <tr>
            <th
              v-for="(col, index) in visibleCols"
              :key="col.key"
              @click="toggleSort(col.key)"
              :title="tooltip(col.key) || undefined"
              class="px-4 py-2.5 font-medium cursor-pointer select-none transition-colors border-b border-[var(--tv-border)] group bg-[var(--tv-bg-card)]"
              :class="[
                sortKey === col.key ? 'text-[var(--tv-text-primary)]' : 'text-[var(--tv-text-muted)] hover:text-[var(--tv-text-secondary)]',
                isNumberCol(col.key) ? 'text-right' : 'text-left',
                index === 0 ? 'pl-4' : '',
                index === visibleCols.length - 1 ? 'pr-4' : ''
              ]"
            >
              <div class="flex items-center gap-1 inline-flex max-w-full">
                <span class="truncate block max-w-[150px] uppercase text-[11px] tracking-wider">{{ col.label }}</span>
                <span v-if="sortKey === col.key" class="text-[10px] text-[var(--tv-accent)]">
                  {{ sortDir === 'asc' ? '▲' : '▼' }}
                </span>
                <span v-else class="text-[10px] opacity-0 group-hover:opacity-30">↕</span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr
            v-for="(row, i) in paginatedData"
            :key="i"
            class="transition-colors hover:bg-gray-50/80 group"
          >
            <td
              v-for="(col, index) in visibleCols"
              :key="col.key"
              :title="String(row[col.key] ?? '-')"
              class="px-4 py-2 whitespace-nowrap"
              :class="[
                isNumberCol(col.key) ? 'text-right font-mono text-[13px] font-medium' : 'text-left text-[13px]',
                signalClass(col.key, row[col.key]),
                index === 0 ? 'font-semibold text-[var(--tv-text-primary)]' : 'text-[var(--tv-text-secondary)]'
              ]"
            >
              <span v-if="isTickerColumn(col.key)" class="ticker-cell">
                <button
                  class="watch-btn"
                  :class="{ active: store.isWatched(String(row[col.key] ?? '')) }"
                  :title="store.isWatched(String(row[col.key] ?? '')) ? 'Remove from watchlist' : 'Add to watchlist'"
                  @click.stop="store.toggleWatchTicker(String(row[col.key] ?? ''))"
                >
                  {{ store.isWatched(String(row[col.key] ?? '')) ? 'WL' : '+' }}
                </button>
                <span class="truncate block max-w-[140px]">{{ formatCell(row[col.key], col.key) }}</span>
              </span>
              <span v-else class="truncate block max-w-[180px]">
                {{ formatCell(row[col.key], col.key) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!filteredData.length" class="text-[var(--tv-text-muted)] text-sm py-16 text-center font-medium">
        No matching rows
      </div>
    </div>
    
    <!-- 分页器 -->
    <div v-if="pageSize && pageSize > 0 && totalPages > 1" class="shrink-0 flex items-center justify-between px-4 py-2 border-t border-[var(--tv-border)] bg-[var(--tv-bg-card)]">
      <div class="text-[11px] text-[var(--tv-text-muted)] font-medium">
        Page <span class="text-[var(--tv-text-primary)] font-bold">{{ currentPage }}</span> of {{ totalPages }}
      </div>
      <div class="flex items-center gap-1">
        <button 
          @click="setPage(currentPage - 1)" 
          :disabled="currentPage === 1"
          class="px-2 py-1 rounded border border-[var(--tv-border)] text-[11px] font-medium hover:bg-gray-50 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
        >
          Prev
        </button>
        <button 
          @click="setPage(currentPage + 1)" 
          :disabled="currentPage === totalPages"
          class="px-2 py-1 rounded border border-[var(--tv-border)] text-[11px] font-medium hover:bg-gray-50 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tv-table-container {
  display: flex;
  flex-direction: column;
  background: var(--tv-bg-card);
  border: 1px solid var(--tv-border);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.02);
}

.screener-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--tv-border);
  background: linear-gradient(180deg, var(--tv-bg-card) 0%, var(--tv-bg-secondary) 100%);
  flex-shrink: 0;
}

.toolbar-left,
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.table-kicker {
  color: var(--tv-text-primary);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.table-count {
  color: var(--tv-text-muted);
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.search-input {
  width: 190px;
  height: 30px;
  border: 1px solid var(--tv-border);
  border-radius: 6px;
  background: var(--tv-bg-secondary);
  color: var(--tv-text-primary);
  font-size: 12px;
  padding: 0 10px;
  outline: none;
}

.search-input:focus {
  border-color: var(--tv-accent);
  background: var(--tv-bg-card);
  box-shadow: 0 0 0 3px var(--tv-accent-soft);
}

.segmented {
  height: 30px;
  display: inline-flex;
  border: 1px solid var(--tv-border);
  border-radius: 6px;
  background: var(--tv-bg-secondary);
  overflow: hidden;
}

.segmented button,
.columns-btn {
  height: 30px;
  padding: 0 10px;
  border: none;
  color: var(--tv-text-secondary);
  font-size: 11px;
  font-weight: 800;
  background: transparent;
  transition: all 0.15s;
}

.segmented button + button {
  border-left: 1px solid var(--tv-border);
}

.segmented button:hover,
.columns-btn:hover {
  color: var(--tv-text-primary);
  background: var(--tv-bg-hover);
}

.segmented button.active {
  color: var(--tv-accent);
  background: var(--tv-bg-card);
  box-shadow: inset 0 -2px 0 var(--tv-accent);
}

.columns-btn {
  border: 1px solid var(--tv-border);
  border-radius: 6px;
  background: var(--tv-bg-card);
}

.ticker-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 180px;
}

.watch-btn {
  width: 26px;
  height: 20px;
  border: 1px solid var(--tv-border);
  border-radius: 5px;
  color: var(--tv-text-muted);
  background: var(--tv-bg-card);
  font-size: 10px;
  font-weight: 900;
  line-height: 1;
  transition: all 0.15s;
}

.watch-btn:hover {
  color: var(--tv-accent);
  border-color: var(--tv-accent);
}

.watch-btn.active {
  color: #ffffff;
  border-color: var(--tv-accent);
  background: var(--tv-accent);
}

table {
  width: 100%;
  border-spacing: 0;
}

.positive { color: var(--tv-green) !important; }
.negative { color: var(--tv-red) !important; }

th { position: relative; }
th::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 1px;
  background: var(--tv-border);
  z-index: 11;
}

@media (max-width: 860px) {
  .screener-toolbar,
  .toolbar-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .toolbar-left,
  .toolbar-actions,
  .search-input {
    width: 100%;
  }
}
</style>
