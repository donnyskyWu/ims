<script setup lang="ts">
import { ref, watch } from "vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import UserSelect from "@/components/UserSelect.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import ExportButton from "@/components/ExportButton.vue";
import { resourceGet } from "@/api/resource";

const open = defineModel<boolean>("open", { required: true });
const props = defineProps<{ userId?: string; realnameId?: string }>();
const userId = ref("");
const result = ref<Record<string, unknown>>({});
const rows = ref<Record<string, unknown>[]>([]);

const columns: TableColumn[] = [
  { key: "assetCode", label: "资产编号", type: "mono" },
  { key: "assetName", label: "名称" },
  { key: "assetTypeLabel", label: "类型" },
  { key: "bindType", label: "绑定方式" },
  { key: "statusLabel", label: "状态" },
  { key: "bindTime", label: "绑定时间" },
  { key: "consistency", label: "一致性" },
];

async function search() {
  const params: Record<string, unknown> = { includeHistory: true };
  let data: Record<string, unknown>;
  if (props.realnameId) {
    params.realnameId = props.realnameId;
    data = await resourceGet("/asset/reverse/by-person/0", params);
  } else if (userId.value) {
    data = await resourceGet(`/asset/reverse/by-person/${userId.value}`, params);
  } else {
    return;
  }
  result.value = data;
  rows.value = (data.list as Record<string, unknown>[]) || [];
}

function exportApi() {
  const params: Record<string, unknown> = {};
  if (props.realnameId) params.realnameId = props.realnameId;
  else params.userId = userId.value;
  return resourceGet("/asset/reverse/export", params);
}

watch(open, (value) => {
  if (!value) return;
  userId.value = props.userId || "";
  if (props.realnameId || userId.value) void search();
});
</script>

<template>
  <DetailDrawer v-model:open="open" title="反查资产" size="M">
    <UserSelect v-if="!realnameId" v-model="userId" allow-disabled placeholder="选择人员，含离职" />
    <button v-if="!realnameId" class="btn btn-pri" type="button" @click="search">查询</button>
    <p v-if="result.banner">{{ result.banner }}</p>
    <p>{{ (result.summary as { text?: string } | undefined)?.text }}</p>
    <DataTable :columns="columns" :data="rows" />
    <ExportButton v-perm="'ims:asset:reverse:export'" :export-api="exportApi" />
  </DetailDrawer>
</template>
