<script setup lang="ts">
import { ref } from "vue";

const collapsed = ref(false);
</script>

<template>
  <div class="split" :class="{ collapsed }">
    <div class="left">
      <slot name="tree" />
    </div>
    <button class="handle" type="button" @click="collapsed = !collapsed">{{ collapsed ? "展开" : "收起" }}</button>
    <div class="right">
      <slot name="main" />
    </div>
  </div>
</template>

<style scoped>
.split { display: flex; gap: 12px; align-items: flex-start; }
.left { width: var(--tree-w); flex: none; max-height: calc(100vh - 120px); overflow: auto; }
.collapsed .left { width: 0; overflow: hidden; }
.right { flex: 1; min-width: 0; max-height: calc(100vh - 120px); overflow: auto; }
.handle { height: 32px; }
</style>
