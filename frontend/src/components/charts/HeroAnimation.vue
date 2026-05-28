<script setup lang="ts">
import { ref } from 'vue'

interface ClickRipple {
  id: number
  x: number
  y: number
}

interface MarketChip {
  symbol: string
  change: string
  tone: 'up' | 'down'
}

const leftMarketChips: MarketChip[] = [
  { symbol: 'NVDA', change: '+1.52%', tone: 'up' },
  { symbol: 'MSFT', change: '+0.86%', tone: 'up' },
  { symbol: 'META', change: '-0.41%', tone: 'down' },
  { symbol: 'AVGO', change: '+2.47%', tone: 'up' },
  { symbol: 'CRM', change: '+0.38%', tone: 'up' },
]

const rightMarketChips: MarketChip[] = [
  { symbol: 'AAPL', change: '+1.24%', tone: 'up' },
  { symbol: 'TSLA', change: '-0.73%', tone: 'down' },
  { symbol: 'AMD', change: '+1.10%', tone: 'up' },
  { symbol: 'ORCL', change: '+0.64%', tone: 'up' },
  { symbol: 'INTC', change: '-0.28%', tone: 'down' },
]

const videoAvailable = ref(true)
const demoImageSrc = '/demo/trading-workflow.gif'
const clickRipples = ref<ClickRipple[]>([])
const isPressing = ref(false)
const clickRippleDurationMs = 1100
const pressFeedbackDurationMs = 260
let rippleId = 0

function handleDemoClick(event: MouseEvent) {
  const target = event.currentTarget as HTMLElement | null
  if (!target) return

  const rect = target.getBoundingClientRect()
  const ripple: ClickRipple = {
    id: rippleId++,
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  }

  clickRipples.value.push(ripple)
  isPressing.value = true

  window.setTimeout(() => {
    clickRipples.value = clickRipples.value.filter(item => item.id !== ripple.id)
  }, clickRippleDurationMs)

  window.setTimeout(() => {
    isPressing.value = false
  }, pressFeedbackDurationMs)
}
</script>

<template>
  <section
    class="demo-video-stage"
    data-testid="recorded-demo"
    :style="{ '--demo-ripple-duration': `${clickRippleDurationMs}ms` }"
    @click="handleDemoClick"
  >
    <div class="demo-video-layout">
      <aside class="demo-market-rail" aria-hidden="true">
        <span
          v-for="chip in leftMarketChips"
          :key="chip.symbol"
          class="demo-market-chip"
          :class="`demo-market-chip--${chip.tone}`"
        >
          <strong>{{ chip.symbol }}</strong>
          <span>{{ chip.change }}</span>
        </span>
      </aside>

      <div class="demo-video-shell" :class="{ 'demo-video-shell--pressing': isPressing }">
        <img
          v-if="videoAvailable"
          class="demo-video"
          :src="demoImageSrc"
          alt="真实前端功能演示"
          @error="videoAvailable = false"
        >
        <div v-else class="demo-video-fallback">
          <strong>真实功能演示录制尚未生成</strong>
          <span>运行 scripts/record_frontend_demo.py 后会自动显示录屏。</span>
        </div>
      </div>

      <aside class="demo-market-rail" aria-hidden="true">
        <span
          v-for="chip in rightMarketChips"
          :key="chip.symbol"
          class="demo-market-chip"
          :class="`demo-market-chip--${chip.tone}`"
        >
          <strong>{{ chip.symbol }}</strong>
          <span>{{ chip.change }}</span>
        </span>
      </aside>
    </div>

    <span
      v-for="ripple in clickRipples"
      :key="ripple.id"
      class="demo-click-ripple"
      :style="{ left: `${ripple.x}px`, top: `${ripple.y}px` }"
    />
  </section>
</template>

<style scoped>
.demo-video-stage {
  position: relative;
  overflow: hidden;
  width: 100%;
  max-width: 1180px;
  margin: 0 auto;
  padding: clamp(12px, 1.8vw, 22px);
  border: 1px solid #d9dee8;
  border-radius: 8px;
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(241, 245, 249, 0.98)),
    #f8fafc;
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.08);
  container-type: inline-size;
  cursor: pointer;
  transition: box-shadow 180ms ease, border-color 180ms ease;
}

.demo-video-stage:hover {
  border-color: rgba(41, 98, 255, 0.28);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.12);
}

.demo-video-layout {
  display: grid;
  grid-template-columns: minmax(86px, 1fr) minmax(0, 900px) minmax(86px, 1fr);
  gap: clamp(10px, 1.3vw, 16px);
  align-items: stretch;
}

.demo-market-rail {
  display: grid;
  align-content: space-between;
  gap: 10px;
  min-width: 0;
  pointer-events: none;
}

.demo-market-chip {
  min-height: 58px;
  padding: 8px 9px;
  border: 1px solid rgba(203, 213, 225, 0.82);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2px;
  overflow: hidden;
}

.demo-market-chip strong {
  color: #334155;
  font-family: Consolas, monospace;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0;
  white-space: nowrap;
}

.demo-market-chip span {
  font-family: Consolas, monospace;
  font-size: 10px;
  font-weight: 900;
  white-space: nowrap;
}

.demo-market-chip--up span {
  color: #059669;
}

.demo-market-chip--down span {
  color: #dc2626;
}

.demo-video-shell {
  position: relative;
  overflow: hidden;
  width: min(100%, 900px);
  aspect-ratio: 16 / 10;
  margin: 0 auto;
  border: 1px solid rgba(15, 23, 42, 0.14);
  border-radius: 7px;
  background: #0f172a;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.12);
  transition:
    transform 240ms cubic-bezier(0.16, 1, 0.3, 1),
    box-shadow 240ms cubic-bezier(0.16, 1, 0.3, 1);
  transform-origin: center center;
}

.demo-video-shell--pressing {
  transform: scale(1.008);
  box-shadow: 0 22px 54px rgba(15, 23, 42, 0.16);
}

.demo-video {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  background: #0f172a;
}

.demo-click-ripple {
  position: absolute;
  z-index: 2;
  width: 18px;
  height: 18px;
  margin-left: -9px;
  margin-top: -9px;
  border-radius: 999px;
  border: 2px solid rgba(255, 255, 255, 0.78);
  background: rgba(41, 98, 255, 0.18);
  pointer-events: none;
  animation: demoClickRipple var(--demo-ripple-duration) cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.demo-video-fallback {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #cbd5e1;
  background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
}

.demo-video-fallback strong {
  color: #ffffff;
  font-size: 16px;
  font-weight: 900;
}

.demo-video-fallback span {
  font-size: 13px;
  font-weight: 700;
}

@keyframes demoClickRipple {
  0% {
    opacity: 0.68;
    transform: scale(0.32);
  }
  55% {
    opacity: 0.4;
    transform: scale(3.2);
  }
  100% {
    opacity: 0;
    transform: scale(5.4);
  }
}

@container (max-width: 1090px) {
  .demo-video-layout {
    grid-template-columns: 1fr;
  }

  .demo-market-rail {
    display: none;
  }
}

@media (max-width: 760px) {
  .demo-video-stage {
    padding: 8px;
    border-radius: 7px;
  }
}
</style>
