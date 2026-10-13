<script setup lang="ts">
import RemoteSelect, { type RemoteOption } from "./RemoteSelect.vue";
import { selectorByIds, selectorPage } from "@/api/resource";

const props = defineProps<{ accountId?: string; ipGroupId?: string; multiple?: boolean }>();
const model = defineModel<string | string[] | null>({ default: null });

function optionOf(row: Record<string, unknown>): RemoteOption {
  return {
    id: String(row.id),
    label: String(row.label || row.authorName || ""),
    extra: row.authorType ? String(row.authorType) : "",
  };
}

function extra() {
  const params: Record<string, unknown> = {};
  if (props.accountId) params.accountId = props.accountId;
  if (props.ipGroupId) params.ipGroupId = props.ipGroupId;
  return params;
}

async function fetch(keyword: string, pageNo: number) {
  const data = await selectorPage("/master/selector/author", keyword, pageNo, extra());
  return { list: (data.list || []).map(optionOf), total: Number(data.total || 0) };
}

async function fetchByIds(ids: string[]) {
  const rows = await selectorByIds("/master/selector/author", ids);
  return rows.map(optionOf);
}
</script>

<template>
  <RemoteSelect v-model="model" :multiple="multiple" placeholder="请选择作者" :fetch="fetch" :fetch-by-ids="fetchByIds" />
</template>
