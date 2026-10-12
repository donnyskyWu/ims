<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ path: { label: string; value?: string }[] }>();
const emit = defineEmits<{ jump: [index: number] }>();

const folded = computed(() => props.path.length > 6);
const head = computed(() => (folded.value ? props.path.slice(0, 1) : props.path));
const tail = computed(() => (folded.value ? props.path.slice(-2) : []));
</script>

<template>
  <nav class="crumb" :title="path.map((item) => item.label).join(' / ')">
    <template v-if="!folded">
      <span v-for="(item, index) in path" :key="index">
        <button v-if="index < path.length - 1" type="button" @click="emit('jump', index)">{{ item.label }}</button>
        <span v-else>{{ item.label }}</span>
        <i v-if="index < path.length - 1"> / </i>
      </span>
    </template>
    <template v-else>
      <button type="button" @click="emit('jump', 0)">{{ head[0].label }}</button>
      <i> / … / </i>
      <span v-for="(item, index) in tail" :key="item.label">
        <button v-if="index < tail.length - 1" type="button" @click="emit('jump', path.length - tail.length + index)">{{ item.label }}</button>
        <span v-else>{{ item.label }}</span>
        <i v-if="index < tail.length - 1"> / </i>
      </span>
    </template>
  </nav>
</template>

<style scoped>
.crumb { font-size: 13px; color: var(--text2); }
button { border: none; background: transparent; color: var(--blue); cursor: pointer; padding: 0; font-size: 13px; }
</style>
