import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const loading = ref(false)
  const taskId = ref<string | null>(null)
  const taskStatus = ref('')
  const taskStep = ref('')
  const taskProgress = ref(0)

  const reportContent = ref('')
  const reportStreaming = ref(false)
  const watchlist = ref<string[]>([])

  if (typeof window !== 'undefined') {
    const savedWatchlist = window.localStorage.getItem('stocks_watchlist')
    if (savedWatchlist) {
      try {
        const parsed = JSON.parse(savedWatchlist)
        if (Array.isArray(parsed)) watchlist.value = parsed.filter(item => typeof item === 'string')
      } catch {
        watchlist.value = []
      }
    }
  }

  function persistWatchlist() {
    if (typeof window === 'undefined') return
    window.localStorage.setItem('stocks_watchlist', JSON.stringify(watchlist.value))
  }

  function setTask(id: string) {
    taskId.value = id
    taskStatus.value = 'PENDING'
    taskStep.value = ''
    taskProgress.value = 0
  }

  function updateTask(status: string, step?: string, progress?: number) {
    taskStatus.value = status
    if (step) taskStep.value = step
    if (progress !== undefined) taskProgress.value = progress
  }

  function resetTask() {
    taskId.value = null
    taskStatus.value = ''
    taskStep.value = ''
    taskProgress.value = 0
  }

  function toggleWatchTicker(ticker: string) {
    const normalizedTicker = ticker.trim().toUpperCase()
    if (!normalizedTicker) return
    watchlist.value = watchlist.value.includes(normalizedTicker)
      ? watchlist.value.filter(item => item !== normalizedTicker)
      : [...watchlist.value, normalizedTicker]
    persistWatchlist()
  }

  function isWatched(ticker: string) {
    return watchlist.value.includes(ticker.trim().toUpperCase())
  }

  return {
    loading,
    taskId,
    taskStatus,
    taskStep,
    taskProgress,
    reportContent,
    reportStreaming,
    watchlist,
    setTask,
    updateTask,
    resetTask,
    toggleWatchTicker,
    isWatched,
  }
})
