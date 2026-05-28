<script setup lang="ts">
import Sidebar from '@/components/layout/Sidebar.vue'
import PipelineProgress from '@/components/layout/PipelineProgress.vue'
import MarketTopBar from '@/components/layout/MarketTopBar.vue'
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-[var(--tv-bg-secondary)]">
    <Sidebar />
    <div class="flex-1 flex flex-col overflow-hidden">
      <MarketTopBar />
      <PipelineProgress />
      <main class="flex-1 overflow-y-auto p-8">
        <router-view v-slot="{ Component, route }">
          <transition name="fade-transform" mode="out-in" appear>
            <component :is="Component" :key="route.fullPath" class="route-view" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>
