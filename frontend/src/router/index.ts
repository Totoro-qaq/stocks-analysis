import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'overview', component: () => import('@/pages/Overview.vue') },
    { path: '/market', name: 'market', component: () => import('@/pages/MarketBenchmark.vue') },
    { path: '/single-stock', name: 'singleStock', component: () => import('@/pages/SingleStock.vue') },
    { path: '/portfolio', name: 'portfolio', component: () => import('@/pages/Portfolio.vue') },
    { path: '/correlation', name: 'correlation', component: () => import('@/pages/Correlation.vue') },
    { path: '/validation', name: 'validation', component: () => import('@/pages/Validation.vue') },
    { path: '/attribution', name: 'attribution', component: () => import('@/pages/FactorAttribution.vue') },
    { path: '/rules', name: 'rules', component: () => import('@/pages/Rules.vue') },
    { path: '/report', name: 'report', component: () => import('@/pages/Report.vue') },
  ],
})

export default router
