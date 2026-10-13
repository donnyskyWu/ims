<script setup lang="ts">
import RemoteSelect, { type RemoteOption } from "./RemoteSelect.vue";
import { selectorByIds, selectorPage } from "@/api/resource";
import { toast } from "@/utils/toast";

const props = defineProps<{ accountId?: string; ipGroupId?: string; multiple?: boolean }>();
const model = defineModel<string | string[] | null>({ default: null });
let emptyTold = false;

function optionOf(row: Record<string, unknown>): RemoteOption {
  return { id: String(row.id), label: String(row.label || row.authorName || "") };
}

function extra() {
  const params: Record<string, unknown> = {};
  if (props.ipGroupId) params.ipGroupId = props.ipGroupId;
  return params;
}

async function fetch(keyword: string, pageNo: number) {
  const data = await selectorPage("/master/selector/author", keyword, pageNo, extra());
  if (!keyword && pageNo === 1 && !data.total && !emptyTold) {
    emptyTold = true;
    toast.info("选择器暂无可选数据");
  }
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
