<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path :d="d" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { icons } from '../nav/menu'

const props = withDefaults(defineProps<{ name: string; size?: number }>(), { size: 16 })
const d = computed(() => icons[props.name] || icons.doc || '')
</script>
