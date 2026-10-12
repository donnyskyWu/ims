<script setup lang="ts">
import RemoteSelect, { type RemoteOption } from "./RemoteSelect.vue";
import { selectorByIds, selectorPage } from "@/api/resource";

defineProps<{ multiple?: boolean }>();
const model = defineModel<string | string[] | null>({ default: null });

function optionOf(row: Record<string, unknown>): RemoteOption {
  const disabled = Boolean(row.disabled) || row.status === "DISABLED";
  return {
    id: String(row.id),
    label: String(row.name || ""),
    disabled,
    reason: disabled ? "已停用" : "",
  };
}

async function fetch(keyword: string, pageNo: number) {
  const data = await selectorPage("/master/selector/company", keyword, pageNo);
  return { list: (data.list || []).map(optionOf), total: Number(data.total || 0) };
}

async function fetchByIds(ids: string[]) {
  const rows = await selectorByIds("/master/selector/company", ids);
  return rows.map(optionOf);
}
</script>

<template>
  <RemoteSelect v-model="model" :multiple="multiple" placeholder="请选择公司" :fetch="fetch" :fetch-by-ids="fetchByIds" />
</template>
