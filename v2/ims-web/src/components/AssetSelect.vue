<script setup lang="ts">
import RemoteSelect, { type RemoteOption } from "./RemoteSelect.vue";
import { selectorByIds, selectorPage } from "@/api/resource";

const props = defineProps<{
  multiple?: boolean;
  kind?: "asset" | "phone";
  assetTypes?: string;
  status?: string;
  ownerUserId?: string;
}>();
const model = defineModel<string | string[] | null>({ default: null });

function extra() {
  if (props.kind === "phone") return {};
  return {
    assetTypes: props.assetTypes || "",
    status: props.status || "",
    ownerUserId: props.ownerUserId || "",
  };
}

function optionOf(row: Record<string, unknown>): RemoteOption {
  if (props.kind === "phone") {
    return { id: String(row.id), label: String(row.label || row.deviceNo || "手机") };
  }
  return { id: String(row.id), label: String(row.label || `${row.assetCode || ""} ${row.assetName || ""}`) };
}

async function fetch(keyword: string, pageNo: number) {
  const url = props.kind === "phone" ? "/master/selector/phone" : "/master/selector/asset";
  const data = await selectorPage(url, keyword, pageNo, extra());
  return { list: (data.list || []).map(optionOf), total: Number(data.total || 0) };
}

async function fetchByIds(ids: string[]) {
  const url = props.kind === "phone" ? "/master/selector/phone" : "/master/selector/asset";
  const rows = await selectorByIds(url, ids);
  return rows.map(optionOf);
}
</script>

<template>
  <RemoteSelect v-model="model" :multiple="multiple" :placeholder="kind === 'phone' ? '请选择手机' : '请选择设备'" :fetch="fetch" :fetch-by-ids="fetchByIds" />
</template>
