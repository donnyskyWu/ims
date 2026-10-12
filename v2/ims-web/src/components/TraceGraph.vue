<script setup lang="ts">
import { ref } from "vue";

export interface GraphNode {
  id: string;
  label: string;
  x: number;
  y: number;
}
defineProps<{ nodes: GraphNode[]; edges: { from: string; to: string }[] }>();
const emit = defineEmits<{ "node-click": [id: string] }>();
const scale = ref(1);
const pan = ref({ x: 0, y: 0 });
let dragging = false;
let last = { x: 0, y: 0 };

function down(event: PointerEvent) {
  dragging = true;
  last = { x: event.clientX, y: event.clientY };
}
function move(event: PointerEvent) {
  if (!dragging) return;
  pan.value = { x: pan.value.x + event.clientX - last.x, y: pan.value.y + event.clientY - last.y };
  last = { x: event.clientX, y: event.clientY };
}
function up() {
  dragging = false;
}
</script>

<template>
  <div class="canvas" @pointerdown="down" @pointermove="move" @pointerup="up" @wheel.prevent="scale = Math.min(2, Math.max(0.4, scale + ($event.deltaY > 0 ? -0.1 : 0.1)))">
    <svg :style="{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})` }">
      <line
        v-for="edge in edges"
        :key="edge.from + edge.to"
        :x1="nodes.find((item) => item.id === edge.from)?.x || 0"
        :y1="nodes.find((item) => item.id === edge.from)?.y || 0"
        :x2="nodes.find((item) => item.id === edge.to)?.x || 0"
        :y2="nodes.find((item) => item.id === edge.to)?.y || 0"
        stroke="currentColor"
      />
      <g v-for="node in nodes" :key="node.id" :transform="`translate(${node.x}, ${node.y})`" @pointerdown.stop @click.stop="emit('node-click', node.id)">
        <rect x="-48" y="-16" width="96" height="32" rx="8" />
        <text text-anchor="middle" y="4">{{ node.label }}</text>
      </g>
    </svg>
  </div>
</template>

<style scoped>
.canvas { height: 320px; overflow: hidden; background: var(--bg); border-radius: var(--r); cursor: grab; color: var(--text2); }
svg { width: 100%; height: 100%; }
rect { fill: var(--card); stroke: var(--line2); }
text { fill: var(--text); font-size: 12px; }
</style>
