<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import DictSelect from "./DictSelect.vue";
import UserSelect from "./UserSelect.vue";
import DeptTreeSelect from "./DeptTreeSelect.vue";

export interface QueryField {
  key: string;
  label: string;
  type: "input" | "select" | "dict" | "date" | "daterange" | "user" | "dept";
  options?: { label: string; value: string }[];
  dictType?: string;
}

const props = withDefaults(
  defineProps<{ fields: QueryField[]; collapseAfter?: number; syncQuery?: boolean }>(),
  { collapseAfter: 4, syncQuery: true },
);
const model = defineModel<Record<string, unknown>>({ required: true });
const emit = defineEmits<{ search: [Record<string, unknown>]; reset: [] }>();
const open = ref(false);
const route = useRoute();
const router = useRouter();
const visible = computed(() => (open.value ? props.fields : props.fields.slice(0, props.collapseAfter)));

function rangeAt(key: string, index: number): string {
  const value = model.value[key];
  return Array.isArray(value) ? String(value[index] || "") : "";
}

function setRange(key: string, index: number, value: string) {
  const current = Array.isArray(model.value[key]) ? [...(model.value[key] as string[])] : ["", ""];
  current[index] = value;
  model.value[key] = current;
}

function trimModel() {
  for (const field of props.fields) {
    const value = model.value[field.key];
    if (typeof value === "string") model.value[field.key] = value.trim();
  }
}

function writeQuery() {
  if (!props.syncQuery) return;
  const query: Record<string, string> = {};
  for (const [key, value] of Object.entries(route.query)) {
    if (!props.fields.some((field) => field.key === key) && key !== "pageNo" && typeof value === "string") query[key] = value;
  }
  for (const field of props.fields) {
    const value = model.value[field.key];
    if (Array.isArray(value)) query[field.key] = value.map(String).join(",");
    else if (value !== undefined && value !== null && String(value) !== "") query[field.key] = String(value);
  }
  query.pageNo = "1";
  void router.replace({ query });
}

function search() {
  trimModel();
  writeQuery();
  emit("search", { ...model.value });
}

function reset() {
  for (const field of props.fields) model.value[field.key] = field.type === "daterange" ? [] : "";
  writeQuery();
  emit("reset");
}

onMounted(() => {
  if (!props.syncQuery) return;
  for (const field of props.fields) {
    const raw = route.query[field.key];
    if (typeof raw !== "string" || raw === "") continue;
    model.value[field.key] = field.type === "daterange" ? raw.split(",") : raw;
  }
});
</script>

<template>
  <form class="qbar" @submit.prevent="search">
    <label v-for="field in visible" :key="field.key" class="item">
      <span>{{ field.label }}</span>
      <input v-if="field.type === 'input'" v-model="model[field.key]" @keyup.enter="search" />
      <select v-else-if="field.type === 'select'" v-model="model[field.key]">
        <option value="">全部</option>
        <option v-for="option in field.options || []" :key="option.value" :value="option.value">{{ option.label }}</option>
      </select>
      <DictSelect v-else-if="field.type === 'dict'" v-model="model[field.key] as string" :dict-type="field.dictType || ''" mode="query" />
      <input v-else-if="field.type === 'date'" v-model="model[field.key]" type="date" />
      <span v-else-if="field.type === 'daterange'" class="range">
        <input :value="rangeAt(field.key, 0)" type="date" @input="setRange(field.key, 0, ($event.target as HTMLInputElement).value)" />
        <input :value="rangeAt(field.key, 1)" type="date" @input="setRange(field.key, 1, ($event.target as HTMLInputElement).value)" />
      </span>
      <UserSelect v-else-if="field.type === 'user'" v-model="model[field.key] as string" />
      <DeptTreeSelect v-else-if="field.type === 'dept'" v-model="model[field.key] as string" />
    </label>
    <button v-if="fields.length > collapseAfter" class="btn btn-txt" type="button" @click="open = !open">{{ open ? "收起" : "更多" }}</button>
    <button class="btn btn-sec btn-sm" type="submit">查询</button>
    <button class="btn btn-sec btn-sm" type="button" @click="reset">重置</button>
  </form>
</template>

<style scoped>
.item { display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--text2); }
input, select { height: 30px; border: 1px solid var(--line2); border-radius: var(--control-r); padding: 0 8px; background: var(--card); color: var(--text); }
.range { display: flex; gap: 4px; }
</style>
