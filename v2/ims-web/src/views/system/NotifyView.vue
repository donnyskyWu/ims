<script setup lang="ts">
import { ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import { systemApi, type Row } from "@/api/system";
import { toast } from "@/utils/toast";

const rows = ref<Row[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(10);
const loading = ref(false);
const query = ref<Row>({ eventType: "", channel: "", status: "" });
const fields: QueryField[] = [
  { key: "eventType", label: "事件", type: "input" },
  { key: "channel", label: "渠道", type: "select", options: [{ label: "站内", value: "SITE" }, { label: "钉钉", value: "DINGTALK" }] },
  { key: "status", label: "状态", type: "select", options: [{ label: "成功", value: "SENT" }, { label: "失败", value: "FAILED" }] },
];
const columns: TableColumn[] = [
  { key: "createTime", label: "时间", type: "time" },
  { key: "eventType", label: "事件" },
  { key: "bizSummary", label: "业务" },
  { key: "receiverName", label: "接收人" },
  { key: "channel", label: "渠道" },
  { key: "statusText", label: "状态" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [{ label: "补发", perm: "ims:system:notify:resend", show: (row) => row.status === "FAILED", onClick: (row) => void resend(row) }],
  },
];

async function load() {
  loading.value = true;
  try {
    const data = await systemApi.notifyPage({ ...query.value, pageNo: pageNo.value, pageSize: pageSize.value });
    rows.value = data.list || [];
    total.value = Number(data.total || 0);
  } finally {
    loading.value = false;
  }
}

async function resend(row: Row) {
  const data = await systemApi.notifyResend(String(row.id));
  toast.success(data.duplicated ? "已有成功记录，未重复发送" : "已补发");
  await load();
}

void load();
</script>

<template>
  <section>
    <PageHeader title="通知" sub-title="只保留发送记录和失败补发。模板与订阅不在本批。" />
    <QueryBar v-model="query" :fields="fields" @search="pageNo = 1; load()" @reset="pageNo = 1; load()" />
    <DataTable :columns="columns" :data="rows" :loading="loading" />
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load" />
  </section>
</template>
