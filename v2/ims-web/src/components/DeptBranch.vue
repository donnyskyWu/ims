<script setup lang="ts">
import type { DeptNode } from "./dept/tree-logic";

const props = defineProps<{
  node: DeptNode;
  expanded: string[];
  selected: string | null;
  keyword: string;
  showCount: boolean;
  dragOver?: string;
  menu: (node: DeptNode) => { key: string; label: string }[];
}>();
const emit = defineEmits<{
  toggle: [id: string];
  select: [id: string];
  menu: [node: DeptNode, key: string];
  drag: [id: string];
  drop: [node: DeptNode];
}>();

const label = () =>
  props.keyword && props.node.name.includes(props.keyword) ? props.node.name.replace(props.keyword, `〖${props.keyword}〗`) : props.node.name;
</script>

<template>
  <li :class="{ on: selected === node.id, ban: dragOver === node.id }">
    <div
      class="row"
      :title="`直属 ${node.directMemberCount} 人，含下级共 ${node.memberCount} 人`"
      draggable="true"
      @click="emit('select', node.id)"
      @dragstart="emit('drag', node.id)"
      @dragover.prevent
      @drop="emit('drop', node)"
    >
      <button type="button" class="exp" @click.stop="emit('toggle', node.id)">{{ expanded.includes(node.id) ? "▾" : "▸" }}</button>
      <span :class="{ off: node.status === 'DISABLED' }">{{ label() }}</span>
      <em v-if="showCount">{{ node.memberCount }}</em>
      <span v-if="node.source === 'LOCAL'" class="mini">本地</span>
      <span v-if="node.localOrphan" class="mini warn">待确认</span>
      <span v-if="node.status === 'DISABLED'" class="mini mute">停用</span>
      <details v-if="menu(node).length" class="more" @click.stop>
        <summary>⋯</summary>
        <div>
          <button v-for="item in menu(node)" :key="item.key" type="button" @click="emit('menu', node, item.key)">{{ item.label }}</button>
        </div>
      </details>
    </div>
    <ul v-if="expanded.includes(node.id)">
      <DeptBranch
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :expanded="expanded"
        :selected="selected"
        :keyword="keyword"
        :show-count="showCount"
        :drag-over="dragOver"
        :menu="menu"
        @toggle="emit('toggle', $event)"
        @select="emit('select', $event)"
        @menu="(node, key) => emit('menu', node, key)"
        @drag="emit('drag', $event)"
        @drop="emit('drop', $event)"
      />
    </ul>
  </li>
</template>

<script lang="ts">
export default { name: "DeptBranch" };
</script>

<style scoped>
.row { display: flex; gap: 4px; align-items: center; min-height: 28px; cursor: pointer; font-size: 13px; }
.on { background: var(--blue-bg); }
.off { color: var(--text2); }
em { color: var(--text2); font-style: normal; }
.mini { font-size: 12px; color: var(--st-info-fg); background: var(--st-info-bg); border-radius: var(--r-xs); padding: 0 4px; }
.warn { color: var(--st-warning-fg); background: var(--st-warning-bg); }
.mute { color: var(--st-neutral-fg); background: var(--st-neutral-bg); }
.exp, summary { border: none; background: transparent; cursor: pointer; }
.more { margin-left: auto; }
ul { list-style: none; margin: 0; padding-left: 12px; }
</style>
