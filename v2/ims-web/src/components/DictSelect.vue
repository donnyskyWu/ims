<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useDictStore } from "@/stores/dict";
import { statusVars } from "@/utils/status-color";

const props = withDefaults(
  defineProps<{ dictType: string; multiple?: boolean; mode?: "create" | "edit" | "query" }>(),
  { mode: "create", multiple: false },
);
const model = defineModel<string | string[] | null>({ default: "" });
const dict = useDictStore();

onMounted(() => {
  void dict.getDict(props.dictType);
});

const current = computed(() => (Array.isArray(model.value) ? model.value : model.value ? [String(model.value)] : []));

const options = computed(() => {
  const items = dict.items(props.dictType);
  if (props.mode === "query") return items;
  return items.filter((item) => item.status !== "DISABLED" || current.value.includes(item.dictValue));
});
</script>

<template>
  <el-select :model-value="model" :multiple="multiple" clearable @update:model-value="model = $event">
    <el-option v-for="item in options" :key="item.dictValue" :label="item.dictLabel" :value="item.dictValue">
      <span class="opt">
        <i class="dot" :style="{ background: statusVars(item.colorType).color }" />
        {{ item.dictLabel }}
        <em v-if="item.status === 'DISABLED'">已停用</em>
      </span>
    </el-option>
  </el-select>
</template>

<style scoped>
.opt { display: inline-flex; align-items: center; gap: 6px; }
.dot { width: 6px; height: 6px; border-radius: 50%; }
em { color: var(--text2); font-style: normal; font-size: 12px; }
</style>
