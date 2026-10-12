<script setup lang="ts">
import RemoteSelect, { type RemoteOption } from "./RemoteSelect.vue";
import { selectorByIds, selectorPage } from "@/api/resource";

const props = withDefaults(defineProps<{ showCertWarning?: boolean; multiple?: boolean }>(), { showCertWarning: true, multiple: false });
const model = defineModel<string | string[] | null>({ default: null });

function optionOf(row: Record<string, unknown>): RemoteOption {
  const disabled = Boolean(row.disabled) || row.status === "DISABLED";
  const expired = Boolean(row.certExpired);
  return {
    id: String(row.id),
    label: String(row.name || ""),
    disabled,
    reason: disabled ? "已停用" : "",
    extra: !disabled && props.showCertWarning && expired ? "证件已过期" : "",
  };
}

async function fetch(keyword: string, pageNo: number) {
  const data = await selectorPage("/master/selector/person", keyword, pageNo);
  return { list: (data.list || []).map((row) => optionOf(row)), total: Number(data.total || 0) };
}

async function fetchByIds(ids: string[]) {
  const rows = await selectorByIds("/master/selector/person", ids);
  return rows.map((row) => optionOf(row));
}
</script>

<template>
  <RemoteSelect v-model="model" :multiple="multiple" :placeholder="'请选择实名人'" :fetch="fetch" :fetch-by-ids="fetchByIds" />
</template>
