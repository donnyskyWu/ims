<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{ type?: "date" | "daterange" | "week" | "month" | "monthrange"; shortcuts?: boolean; maxRange?: number }>(),
  { type: "daterange", shortcuts: true },
);
const model = defineModel<string | string[] | null>({ default: null });
const error = computed(() => {
  if (!props.maxRange || !Array.isArray(model.value) || model.value.length < 2) return "";
  const start = new Date(model.value[0]).getTime();
  const end = new Date(model.value[1]).getTime();
  const days = Math.round((end - start) / 86400000);
  return days > props.maxRange ? `区间不能超过 ${props.maxRange} 天` : "";
});

function applyShortcut(key: string) {
  const today = new Date();
  const iso = (date: Date) => date.toISOString().slice(0, 10);
  const month = (date: Date) => date.toISOString().slice(0, 7);
  if (key === "今天") model.value = [iso(today), iso(today)];
  if (key === "近7天") {
    const start = new Date(today);
    start.setDate(today.getDate() - 6);
    model.value = [iso(start), iso(today)];
  }
  if (key === "近30天") {
    const start = new Date(today);
    start.setDate(today.getDate() - 29);
    model.value = [iso(start), iso(today)];
  }
  if (key === "本月") model.value = props.type === "month" ? month(today) : [iso(new Date(today.getFullYear(), today.getMonth(), 1)), iso(today)];
  if (key === "上月") {
    const start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
    const end = new Date(today.getFullYear(), today.getMonth(), 0);
    model.value = props.type === "month" ? month(start) : [iso(start), iso(end)];
  }
}

const display = computed(() => {
  if (Array.isArray(model.value)) return model.value.filter(Boolean).join(" ~ ");
  return model.value || "";
});
</script>

<template>
  <div>
    <div v-if="shortcuts" class="shortcuts">
      <button v-for="item in ['今天', '近7天', '近30天', '本月', '上月']" :key="item" type="button" class="btn btn-sec btn-sm" @click="applyShortcut(item)">{{ item }}</button>
    </div>
    <el-date-picker
      v-if="type !== 'week'"
      :model-value="model"
      :type="type === 'monthrange' ? 'monthrange' : type"
      value-format="YYYY-MM-DD"
      @update:model-value="model = $event"
    />
    <el-date-picker v-else :model-value="model" type="week" @update:model-value="model = $event" />
    <p v-if="display" class="muted">{{ display }}</p>
    <p v-if="error" class="ferr">{{ error }}</p>
  </div>
</template>

<style scoped>
.shortcuts { display: flex; gap: 6px; margin-bottom: 8px; flex-wrap: wrap; }
</style>
