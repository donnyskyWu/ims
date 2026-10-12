<script setup lang="ts">
import { ref } from "vue";
import DeptTree from "@/components/DeptTree.vue";

const selected = ref<string | null>(null);
const includeChildren = ref(true);
const logs = ref<string[]>([]);

function onSelect(id: string | null, inc: boolean) {
  logs.value.push(id ? `select(${id}, ${inc ? "含下级" : "仅本级"})` : "select(全部)");
}
</script>

<template>
  <section class="split">
    <DeptTree v-model:selected="selected" v-model:include-children="includeChildren" @select="onSelect" />
    <div>
      <h1>部门树</h1>
      <p class="muted">事件日志</p>
      <ol>
        <li v-for="(item, index) in logs" :key="index">{{ item }}</li>
      </ol>
    </div>
  </section>
</template>

<style scoped>
.split { display: flex; gap: 16px; }
h1 { font-size: 28px; }
</style>
