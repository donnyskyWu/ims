<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ items: { key: string; label: string }[]; closable?: boolean }>();
const emit = defineEmits<{ close: [key: string]; clear: [] }>();
const shown = computed(() => props.items.slice(0, 5));
const extra = computed(() => Math.max(0, props.items.length - 5));
</script>

<template>
  <div v-if="items.length" class="row">
    <span v-for="item in shown" :key="item.key" class="chip">
      {{ item.label }}
      <button v-if="closable" type="button" @click="emit('close', item.key)">×</button>
    </span>
    <span v-if="extra" class="chip">+{{ extra }}</span>
    <button v-if="closable" class="btn btn-txt" type="button" @click="emit('clear')">清空</button>
  </div>
</template>

<style scoped>
.row { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
button { border: none; background: transparent; cursor: pointer; color: var(--text2); }
</style>
