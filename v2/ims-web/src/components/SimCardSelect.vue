<script setup lang="ts">
import RemoteSelect, { type RemoteOption } from "./RemoteSelect.vue";
import { selectorByIds, selectorPage } from "@/api/resource";

const props = defineProps<{ multiple?: boolean; params?: Record<string, unknown> }>();
const model = defineModel<string | string[] | null>({ default: null });

function optionOf(row: Record<string, unknown>): RemoteOption {
  const disabled = Boolean(row.disabled) || row.status === "DISABLED";
  const name = String(row.realnameName || "");
  return {
    id: String(row.id),
    label: `${String(row.phoneMasked || "手机卡")}${name ? " · " + name : ""}`,
    disabled,
    reason: disabled ? "已停用" : "",
  };
}

async function fetch(keyword: string, pageNo: number) {
  const data = await selectorPage("/master/selector/sim-card", keyword, pageNo, props.params);
  return { list: (data.list || []).map(optionOf), total: Number(data.total || 0) };
}

async function fetchByIds(ids: string[]) {
  const rows = await selectorByIds("/master/selector/sim-card", ids);
  return rows.map(optionOf);
}
</script>

<template>
  <RemoteSelect v-model="model" :multiple="multiple" placeholder="请选择手机卡" :fetch="fetch" :fetch-by-ids="fetchByIds" />
</template>
