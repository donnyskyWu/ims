<script setup lang="ts">
import RemoteSelect, { type RemoteOption } from "./RemoteSelect.vue";
import { selectorByIds, selectorPage } from "@/api/resource";

const props = defineProps<{ platform?: string; status?: string; ipGroupId?: string; multiple?: boolean; liveOnly?: boolean }>();
const model = defineModel<string | string[] | null>({ default: null });

function optionOf(row: Record<string, unknown>): RemoteOption {
  const disabled = row.status === "CANCELLED";
  const label = String(row.label || `${row.accountNo || ""} ${row.nickname || ""}`).trim();
  return { id: String(row.id), label, disabled, reason: disabled ? "已注销" : "" };
}

function extra() {
  const params: Record<string, unknown> = {};
  if (props.platform) params.platform = props.platform;
  if (props.status) params.status = props.status;
  if (props.ipGroupId) params.ipGroupId = props.ipGroupId;
  if (props.liveOnly) params.liveOnly = 1;
  return params;
}

async function fetch(keyword: string, pageNo: number) {
  const data = await selectorPage("/master/selector/account", keyword, pageNo, extra());
  return { list: (data.list || []).map(optionOf), total: Number(data.total || 0) };
}

async function fetchByIds(ids: string[]) {
  const rows = await selectorByIds("/master/selector/account", ids);
  return rows.map(optionOf);
}
</script>

<template>
  <RemoteSelect v-model="model" :multiple="multiple" placeholder="请选择平台账号" :fetch="fetch" :fetch-by-ids="fetchByIds" />
</template>
