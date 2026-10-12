<script setup lang="ts">
import { ref } from "vue";
import { fmtTime } from "@/utils/format";
import EmptyState from "./EmptyState.vue";
import { statusVars } from "@/utils/status-color";

defineProps<{ items: { time: string; title: string; operator?: string; detail?: string; colorType?: string }[] }>();
const opened = ref<Record<number, boolean>>({});
</script>

<template>
  <EmptyState v-if="!items.length" />
  <ol v-else class="tl">
    <li v-for="(item, index) in items" :key="index">
      <i :style="{ background: statusVars(item.colorType || 'primary').color }" />
      <div>
        <strong>{{ item.title }}</strong>
        <span class="muted"> {{ fmtTime(item.time) }} {{ item.operator || "" }}</span>
        <button v-if="item.detail" class="btn btn-txt" type="button" @click="opened[index] = !opened[index]">{{ opened[index] ? "收起" : "展开" }}</button>
        <p v-if="opened[index]">{{ item.detail }}</p>
      </div>
    </li>
  </ol>
</template>

<style scoped>
.tl { list-style: none; margin: 0; padding: 0; }
.tl li { display: flex; gap: 8px; padding: 8px 0; }
.tl i { width: 8px; height: 8px; border-radius: 50%; margin-top: 6px; }
</style>
