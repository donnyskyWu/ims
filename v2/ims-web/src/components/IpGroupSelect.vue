<script setup lang="ts">
import RemoteSelect, { type RemoteOption } from "./RemoteSelect.vue";
import { selectorByIds, selectorPage } from "@/api/resource";

const props = defineProps<{ multiple?: boolean; onlySmall?: boolean }>();
const model = defineModel<string | string[] | null>({ default: null });

function optionOf(row: Record<string, unknown>): RemoteOption {
  return { id: String(row.id), label: String(row.label || row.groupName || "") };
}

function extra() {
  const params: Record<string, unknown> = {};
  if (props.onlySmall) params.onlySmall = true;
  return params;
}

async function fetch(keyword: string, pageNo: number) {
  const data = await selectorPage("/master/selector/ip-group", keyword, pageNo, extra());
  return { list: (data.list || []).map(optionOf), total: Number(data.total || 0) };
}

async function fetchByIds(ids: string[]) {
  const rows = await selectorByIds("/master/selector/ip-group", ids);
  return rows.map(optionOf);
}
</script>

<template>
  <RemoteSelect v-model="model" :multiple="multiple" placeholder="请选择分组" :fetch="fetch" :fetch-by-ids="fetchByIds" />
</template>
