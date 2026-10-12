<script setup lang="ts">
import { onMounted, ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import StatCard, { type StatItem } from "@/components/StatCard.vue";
import ChartPanel from "@/components/ChartPanel.vue";
import Perm from "@/components/Perm.vue";
import { toast } from "@/utils/toast";
import { flowApi, type Row } from "./api";

const query = ref<Record<string, unknown>>({ businessDomain: "", templateName: "", assigneeUserId: "" });
const fields: QueryField[] = [
  { key: "businessDomain", label: "业务域", type: "dict", dictType: "dict_flow_domain" },
  { key: "templateName", label: "模板", type: "input" },
  { key: "assigneeUserId", label: "处理人", type: "user" },
];
const rows = ref<Row[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const stats = ref<StatItem[]>([]);
const dimension = ref("TEMPLATE");
const chart = ref<{ name: string; value: number }[]>([]);
const columns: TableColumn[] = [
  { key: "instanceNo", label: "实例号", type: "mono" },
  { key: "templateName", label: "流程" },
  { key: "nodeName", label: "节点" },
  { key: "assigneeName", label: "处理人" },
  { key: "timeoutDurationMinutes", label: "超时（分钟）", type: "number" },
  { key: "remindCount", label: "催办次数", type: "number" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [{ label: "督办", perm: "ims:flow:timeout:urge", onClick: (row) => void urge(String(row.id)) }],
  },
];

async function load() {
  const data = await flowApi.timeouts({ ...query.value, pageNo: pageNo.value, pageSize: pageSize.value });
  rows.value = data.list || [];
  total.value = data.total || 0;
  const rate = await flowApi.timeoutRate();
  stats.value = [
    { title: "本月超时率", value: Number(rate.monthlyTimeoutRate || 0), format: "percent" },
    { title: "目标", value: Number(rate.targetRate || 0), format: "percent" },
  ];
  const dist = await flowApi.timeoutDistribution(dimension.value);
  chart.value = (dist || []).map((item) => ({ name: String(item.dimensionValue || ""), value: Number(item.timeoutCount || 0) }));
}

async function urge(id: string) {
  await flowApi.urge(id, "请尽快处理已超时的审批");
  toast.success("已发送督办");
  await load();
}

onMounted(load);
</script>

<template>
  <section>
    <PageHeader title="超时督办" sub-title="按任务逾期催办，实例超时标记不阻止办理" />
    <StatCard :items="stats" :cols="3" />
    <QueryBar v-model="query" :fields="fields" @search="() => { pageNo = 1; load(); }" @reset="load" />
    <DataTable :columns="columns" :data="rows" @retry="load">
      <template #cell-timeoutDurationMinutes="{ row }">
        <span class="timeout">{{ row.timeoutDurationMinutes }}</span>
      </template>
    </DataTable>
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load" />
    <div class="bar">
      <label>分布
        <select v-model="dimension" @change="load">
          <option value="TEMPLATE">模板</option>
          <option value="NODE">节点</option>
          <option value="DEPT">部门</option>
          <option value="PERSON">人员</option>
        </select>
      </label>
      <Perm code="ims:flow:timeout:query" />
    </div>
    <ChartPanel type="bar" :data="chart" />
  </section>
</template>

<style scoped>
.timeout { color: var(--red, #c45656); }
.bar { margin: 12px 0; }
</style>
