<script setup lang="ts">
withDefaults(defineProps<{ d: string; size?: number }>(), { size: 16 })
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
    <path :d="d" />
  </svg>
</template>
