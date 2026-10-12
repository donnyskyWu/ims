<script setup lang="ts">
import TraceGraph, { type GraphNode } from "./TraceGraph.vue";

defineProps<{ nodes: GraphNode[]; edges: { from: string; to: string }[]; selected?: string }>();
const emit = defineEmits<{ "node-click": [id: string] }>();
</script>

<template>
  <div class="dag">
    <aside class="side">组件</aside>
    <TraceGraph :nodes="nodes" :edges="edges" @node-click="emit('node-click', $event)" />
    <aside class="prop">
      <p class="muted">节点信息</p>
      <p>{{ selected || "未选择" }}</p>
    </aside>
  </div>
</template>

<style scoped>
.dag {
  display: grid;
  grid-template-columns: var(--designer-side) 1fr var(--designer-prop);
  min-height: 360px;
  background-image: linear-gradient(var(--line) 1px, transparent 1px), linear-gradient(90deg, var(--line) 1px, transparent 1px);
  background-size: var(--grid) var(--grid);
  border: 1px solid var(--line);
  border-radius: var(--r);
}
.side, .prop { background: var(--card); padding: 12px; }
</style>
