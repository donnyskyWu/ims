<script setup lang="ts">
import { onMounted, ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import { toast } from "@/utils/toast";
import { resourcePage, resourceSend } from "@/api/resource";

const rows = ref<Record<string, unknown>[]>([]);
const loading = ref(false);
const columns: TableColumn[] = [
  { key: "label", label: "任务" },
  { key: "name", label: "标识", type: "mono" },
  { key: "cron", label: "周期" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [{ label: "执行", perm: "ims:system:job:run", onClick: (row) => void run(row) }],
  },
];

async function load() {
  loading.value = true;
  try {
    const data = await resourcePage<Record<string, unknown>>("/system/job/page", { pageNo: 1, pageSize: 50 });
    rows.value = data.list;
  } finally {
    loading.value = false;
  }
}
async function run(row: Record<string, unknown>) {
  await resourceSend("POST", "/system/job/run", { name: row.name });
  toast.success("已执行");
}
onMounted(load);
</script>

<template>
  <section class="page">
    <PageHeader title="定时任务" sub-title="系统管理 / 定时任务" />
    <DataTable :columns="columns" :data="rows" :loading="loading" />
  </section>
</template>
