<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{
  content: string
}>()

const html = computed(() => {
  if (!props.content) return ''
  return marked(props.content)
})
</script>

<template>
  <div class="prose prose-invert max-w-none" v-html="html" />
</template>
