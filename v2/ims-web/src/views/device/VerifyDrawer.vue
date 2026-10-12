<script setup lang="ts">
import { ref, watch } from "vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import AppTabs from "@/components/AppTabs.vue";
import StatCard from "@/components/StatCard.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import ChartPanel from "@/components/ChartPanel.vue";
import UserSelect from "@/components/UserSelect.vue";
import AppModal from "@/components/AppModal.vue";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";

const open = defineModel<boolean>("open", { required: true });
const props = defineProps<{ taskId?: string }>();
const tab = ref("batch");
const metrics = ref<Record<string, unknown>>({});
const showTrend = ref(false);
const batches = ref<Record<string, unknown>[]>([]);
const tasks = ref<Record<string, unknown>[]>([]);
const running = ref(false);
const dealOpen = ref(false);
const current = ref<Record<string, unknown> | null>(null);
const ownerUserId = ref("");
const deadline = ref("");
const remark = ref("");

const batchColumns: TableColumn[] = [
  { key: "batchNo", label: "批次号", type: "mono" },
  { key: "verifyTypeLabel", label: "校验类型" },
  { key: "triggerLabel", label: "触发方式" },
  { key: "totalCount", label: "校验总数" },
  { key: "errorCount", label: "异常数" },
  { key: "pendingCount", label: "待处理工单" },
  { key: "createTime", label: "批次时间", type: "time" },
  { key: "ops", label: "操作", type: "actions", actions: [{ label: "查看明细", onClick: (row) => void openBatch(row) }] },
];
const taskColumns: TableColumn[] = [
  { key: "taskNo", label: "工单号", type: "mono" },
  { key: "batchNo", label: "批次号" },
  { key: "assetCode", label: "资产编号" },
  { key: "assetName", label: "资产名称" },
  { key: "fieldText", label: "不一致字段" },
  { key: "statusLabel", label: "状态" },
  { key: "ownerName", label: "修复责任人" },
  { key: "deadline", label: "限期" },
  {
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [
      { label: "处理", show: (row) => row.taskStatus === "PENDING_DISPATCH" || row.taskStatus === "REPAIRING", onClick: (row) => openTask(row) },
      { label: "复审", perm: "ims:asset:verify:recheck", show: (row) => row.taskStatus === "PENDING_RECHECK", onClick: (row) => openTask(row) },
    ],
  },
];

async function load() {
  metrics.value = await resourceGet("/asset/verify/metrics");
  const batch = await resourcePage<Record<string, unknown>>("/asset/verify/batches", { pageNo: 1, pageSize: 20 });
  batches.value = batch.list;
  const params: Record<string, unknown> = { pageNo: 1, pageSize: 50 };
  if (props.taskId) params.taskId = props.taskId;
  const error = await resourcePage<Record<string, unknown>>("/asset/verify/errors", params);
  tasks.value = error.list;
  if (props.taskId && error.list[0]) {
    tab.value = "error";
    openTask(error.list[0]);
  }
}

async function run() {
  running.value = true;
  try {
    const data = await resourceSend<{ message?: string }>("POST", "/asset/verify/run", { verifyTypes: ["asset_person"], scope: "FULL" }, `verify-${Date.now()}`);
    toast.success(data.message || "校验完成");
    await load();
  } finally {
    running.value = false;
  }
}

function openBatch(row: Record<string, unknown>) {
  tab.value = "error";
  void resourcePage<Record<string, unknown>>("/asset/verify/errors", { pageNo: 1, pageSize: 50, batchNo: row.batchNo }).then((data) => {
    tasks.value = data.list;
  });
}
function openTask(row: Record<string, unknown>) {
  current.value = row;
  ownerUserId.value = String(row.ownerUserId || "");
  deadline.value = String(row.deadline || "");
  remark.value = "";
  dealOpen.value = true;
}
async function send(action: string) {
  if (!current.value) return;
  await resourceSend("PUT", `/asset/verify/task/${current.value.id}`, { action, ownerUserId: ownerUserId.value, deadline: deadline.value, remark: remark.value });
  dealOpen.value = false;
  toast.success("已提交");
  await load();
}
async function pass() {
  await confirm({ title: "复审通过", message: "通过后工单闭环，待办完成。", action: () => send("RECHECK_PASS") });
}
function trendOf(key: "completeness" | "consistency") {
  const rows = (metrics.value.trend as { date?: string; completeness?: number | null; consistency?: number | null }[]) || [];
  return rows.filter((item) => item[key] != null).map((item) => ({ name: String(item.date || ""), value: Number(item[key] || 0) * 100 }));
}

watch(open, (value) => {
  if (value) void load();
});
</script>

<template>
  <DetailDrawer v-model:open="open" title="关联校验" size="F">
    <StatCard
      :items="[
        { title: '资产关联完整率', value: String(metrics.completeness || '—'), onClick: () => (showTrend = !showTrend) },
        { title: '校验一致率', value: String(metrics.consistency || '—'), desc: metrics.consistencyWarn ? '低于 98%' : '', onClick: () => (showTrend = !showTrend) },
        { title: '待处理工单', value: Number(metrics.openCount || 0) },
        { title: '本周批次', value: Number(metrics.weekBatchCount || 0) },
      ]"
    />
    <button v-perm="'ims:asset:verify:run'" class="btn btn-pri" type="button" :disabled="running" @click="run">{{ running ? "执行中" : "手动触发校验" }}</button>
    <div v-if="showTrend" class="trend">
      <ChartPanel type="line" :data="trendOf('completeness')" />
      <ChartPanel type="line" :data="trendOf('consistency')" />
    </div>
    <AppTabs v-model:active="tab" :items="[{ key: 'batch', label: '批次列表' }, { key: 'error', label: '异常工单' }]" />
    <DataTable v-if="tab === 'batch'" :columns="batchColumns" :data="batches" />
    <DataTable v-else :columns="taskColumns" :data="tasks" />
    <AppModal v-model:open="dealOpen" title="处理工单" :width="560">
      <p>{{ current?.assetCode }} {{ current?.assetName }}</p>
      <p>{{ current?.fieldText }} <span v-if="Number(current?.overdueDays) > 0">逾期 {{ current?.overdueDays }} 天</span></p>
      <template v-if="current?.taskStatus === 'PENDING_DISPATCH'">
        <el-form-item label="修复责任人"><UserSelect v-model="ownerUserId" /></el-form-item>
        <el-form-item label="限期"><el-input v-model="deadline" placeholder="默认 3 个工作日" /></el-form-item>
        <button v-perm="'ims:asset:verify:dispatch'" class="btn btn-pri" type="button" @click="send('DISPATCH')">派发</button>
      </template>
      <template v-else-if="current?.taskStatus === 'REPAIRING'">
        <el-form-item label="修复说明"><el-input v-model="remark" maxlength="512" type="textarea" /></el-form-item>
        <button class="btn btn-pri" type="button" @click="send('SUBMIT_FIX')">提交修复</button>
      </template>
      <template v-else-if="current?.taskStatus === 'PENDING_RECHECK'">
        <p>修复说明：{{ current?.fixRemark }}</p>
        <el-form-item label="复审意见"><el-input v-model="remark" maxlength="512" type="textarea" /></el-form-item>
        <button v-perm="'ims:asset:verify:recheck'" class="btn btn-pri" type="button" @click="pass">通过</button>
        <button v-perm="'ims:asset:verify:recheck'" class="btn btn-sec" type="button" @click="send('RECHECK_REJECT')">退回</button>
      </template>
    </AppModal>
  </DetailDrawer>
</template>
