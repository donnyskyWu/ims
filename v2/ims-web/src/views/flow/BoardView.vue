<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import StatCard, { type StatItem } from "@/components/StatCard.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import ChartPanel from "@/components/ChartPanel.vue";
import { flowApi, type Row } from "./api";

const router = useRouter();
const query = ref<Record<string, unknown>>({ businessDomain: "", dateRange: ["", ""] });
const fields: QueryField[] = [
  { key: "businessDomain", label: "业务域", type: "dict", dictType: "dict_flow_domain" },
  { key: "dateRange", label: "日期", type: "daterange" },
];
const stats = ref<StatItem[]>([]);
const byTemplate = ref<Row[]>([]);
const byNode = ref<Row[]>([]);
const recent = ref<Row[]>([]);
const chart = ref<{ name: string; value: number }[]>([]);

const templateColumns: TableColumn[] = [
  { key: "templateName", label: "模板" },
  { key: "runningCount", label: "进行中", type: "number" },
  { key: "timeoutCount", label: "超时", type: "number" },
  { key: "avgDurationHours", label: "平均时长（小时）", type: "number" },
];
const nodeColumns: TableColumn[] = [
  { key: "nodeName", label: "节点" },
  { key: "pendingCount", label: "待处理", type: "number" },
  { key: "timeoutCount", label: "超时", type: "number" },
];
const recentColumns: TableColumn[] = [
  { key: "instanceNo", label: "实例号", type: "mono" },
  { key: "templateName", label: "流程" },
  { key: "nodeName", label: "节点" },
  { key: "assigneeName", label: "处理人" },
  { key: "slaDeadline", label: "截止", type: "time" },
  { key: "ops", label: "操作", type: "actions", actions: [{ label: "去督办", onClick: () => void router.push("/ims/flow/timeout") }] },
];

async function load() {
  const range = Array.isArray(query.value.dateRange) ? (query.value.dateRange as string[]) : [];
  const data = await flowApi.board({
    businessDomain: query.value.businessDomain,
    dateFrom: range[0],
    dateTo: range[1],
  });
  stats.value = [
    { title: "进行中", value: Number(data.runningCount || 0) },
    { title: "超时", value: Number(data.timeoutCount || 0) },
    { title: "已完成", value: Number(data.finishedCount || 0) },
    { title: "超时率", value: Number(data.timeoutRate || 0), format: "percent" },
  ];
  byTemplate.value = (data.byTemplate as Row[]) || [];
  byNode.value = (data.byNode as Row[]) || [];
  recent.value = (data.recentTimeout as Row[]) || [];
  chart.value = byTemplate.value.map((row) => ({ name: String(row.templateName || ""), value: Number(row.runningCount || 0) }));
}

let timer = 0;
onMounted(() => {
  void load();
  timer = window.setInterval(() => void load(), 60000);
});
onBeforeUnmount(() => window.clearInterval(timer));
</script>

<template>
  <section>
    <PageHeader title="流程看板" sub-title="进行中、超时和完成情况" />
    <QueryBar v-model="query" :fields="fields" @search="load" @reset="load" />
    <StatCard :items="stats" />
    <ChartPanel type="bar" :data="chart" />
    <h2>按模板</h2>
    <DataTable :columns="templateColumns" :data="byTemplate" />
    <h2>按节点</h2>
    <DataTable :columns="nodeColumns" :data="byNode" />
    <h2>近期超时</h2>
    <DataTable :columns="recentColumns" :data="recent" />
  </section>
</template>
