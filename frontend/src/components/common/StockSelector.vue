<script setup lang="ts">
defineProps<{ modelValue: string; options: { ticker: string; name: string }[] }>()
defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <select
    :value="modelValue"
    @change="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
    data-testid="stock-selector"
    class="tv-select"
  >
    <option v-for="opt in options" :key="opt.ticker" :value="opt.ticker">
      {{ opt.ticker }} — {{ opt.name }}
    </option>
  </select>
</template>

<style scoped>
.tv-select {
  width: 100%;
  background: var(--tv-bg-primary);
  border: 1px solid var(--tv-border);
  border-radius: 6px;
  padding: 8px 10px;
  color: var(--tv-text-primary);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
}
.tv-select:focus { outline: none; border-color: var(--tv-accent); }
.tv-select option {
  background: var(--tv-bg-card);
  color: var(--tv-text-primary);
}
</style>
