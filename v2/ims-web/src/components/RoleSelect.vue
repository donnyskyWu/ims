<script setup lang="ts">
import { onMounted, ref } from "vue";
import { call } from "@/api/generated/endpoints";
import { useDictStore } from "@/stores/dict";

const model = defineModel<string | string[] | null>({ default: null });
const props = withDefaults(defineProps<{ multiple?: boolean }>(), { multiple: false });
const dict = useDictStore();
const options = ref<{ id: string; name: string; source: string; status: string }[]>([]);

onMounted(async () => {
  void dict.getDict("dict_role_source");
  const data = await call<unknown>("role_simple_admin_api_ims_system_role_simple_list_get", { silent: true });
  const list = Array.isArray(data) ? data : ((data as { list?: unknown[] }).list ?? []);
  options.value = (list as Record<string, unknown>[]).map((row) => ({
    id: String(row.id),
    name: String(row.name || ""),
    source: String(row.source || ""),
    status: String(row.status || "ENABLED"),
  }));
});

function blocked(row: { status: string; name: string }) {
  return row.status === "DISABLED" || row.status === "PENDING_CONFIG" || row.name.includes("待配置");
}
</script>

<template>
  <el-select :model-value="model" :multiple="props.multiple" clearable filterable @update:model-value="model = $event">
    <el-option v-for="item in options" :key="item.id" :label="item.name" :value="item.id" :disabled="blocked(item)">
      <span>{{ item.name }}</span>
      <em class="src">{{ dict.label("dict_role_source", item.source) }}</em>
    </el-option>
  </el-select>
</template>

<style scoped>
.src { margin-left: 8px; color: var(--text2); font-style: normal; font-size: 12px; }
</style>
