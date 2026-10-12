<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import AppTabs from "@/components/AppTabs.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import Perm from "@/components/Perm.vue";
import UserSelect from "@/components/UserSelect.vue";
import { confirm } from "@/components/confirm";
import { toast } from "@/utils/toast";
import { flowApi, type Row } from "./api";

const route = useRoute();
const tab = ref("todo");
const badge = ref(0);
const query = ref<Record<string, unknown>>({ businessDomain: "", instanceStatus: "", taskStatus: "" });
const pageNo = ref(1);
const pageSize = ref(20);
const total = ref(0);
const rows = ref<Row[]>([]);
const loading = ref(false);
const detailOpen = ref(false);
const detail = ref<Row | null>(null);
const handleOpen = ref(false);
const handling = ref<Row | null>(null);
const handleForm = ref({ action: "APPROVE", comment: "", rejectToNodeOrder: "", transferReason: "" });
const transferUser = ref<string | null>(null);
const fields = computed<QueryField[]>(() => {
  if (tab.value === "todo") return [{ key: "businessDomain", label: "业务域", type: "dict", dictType: "dict_flow_domain" }];
  if (tab.value === "initiated") return [{ key: "instanceStatus", label: "状态", type: "dict", dictType: "dict_flow_instance_status" }];
  return [{ key: "taskStatus", label: "处理结果", type: "dict", dictType: "dict_flow_task_status" }];
});

const columns = computed<TableColumn[]>(() => {
  if (tab.value === "initiated") {
    return [
      { key: "instanceNo", label: "实例号", type: "mono" },
      { key: "templateName", label: "流程" },
      { key: "assigneeBrief", label: "当前处理人" },
      { key: "instanceStatus", label: "状态", type: "status", dictType: "dict_flow_instance_status" },
      { key: "startedAt", label: "发起时间", type: "time" },
      {
        key: "ops",
        label: "操作",
        type: "actions",
        actions: [
          { label: "详情", onClick: (row) => void openDetail(String(row.instanceNo || "")) },
          { label: "撤销", perm: "ims:flow:instance:cancel", show: (row) => Boolean(row.canRevoke), onClick: (row) => void revoke(String(row.instanceNo || "")) },
        ],
      },
    ];
  }
  return [
    { key: "instanceNo", label: "实例号", type: "mono" },
    { key: "templateName", label: "流程" },
    { key: "nodeName", label: "节点" },
    { key: "initiatorName", label: "发起人" },
    { key: "slaDeadline", label: "SLA 截止", type: "time" },
    { key: "taskStatus", label: "状态", type: "status", dictType: "dict_flow_task_status" },
    { key: "durationMinutes", label: "处理时长（分钟）", type: "number" },
    {
      key: "ops",
      label: "操作",
      type: "actions",
      actions: [
        { label: "处理", perm: "ims:flow:task:handle", show: (row) => tab.value === "todo" && row.nodeType !== "TIMER", onClick: (row) => openHandle(row) },
        { label: "详情", onClick: (row) => void openDetail(String(row.instanceNo || "")) },
      ],
    },
  ];
});

async function load() {
  loading.value = true;
  try {
    const params = { ...query.value, pageNo: pageNo.value, pageSize: pageSize.value };
    const data =
      tab.value === "todo"
        ? await flowApi.myTodo(params)
        : tab.value === "initiated"
          ? await flowApi.myInitiated(params)
          : await flowApi.myHandled(params);
    rows.value = (data.list || []).map((row) => ({
      ...row,
      assigneeBrief: Array.isArray(row.currentNodes)
        ? (row.currentNodes as Row[]).map((item) => String(item.assigneeName || "")).filter(Boolean).join("、")
        : "",
    }));
    total.value = data.total || 0;
    const mark = await flowApi.badge();
    badge.value = mark.count || 0;
  } finally {
    loading.value = false;
  }
}

function search() {
  pageNo.value = 1;
  void load();
}

async function openDetail(instanceNo: string) {
  if (!instanceNo) return;
  detail.value = await flowApi.detail(instanceNo);
  detailOpen.value = true;
}

function openHandle(row: Row) {
  handling.value = row;
  transferUser.value = null;
  handleForm.value = { action: "APPROVE", comment: "", rejectToNodeOrder: "", transferReason: "" };
  handleOpen.value = true;
}

async function submitHandle(model: Record<string, unknown>) {
  const id = String(handling.value?.id || "");
  if (model.action === "TRANSFER") {
    await flowApi.transfer(id, { toUserId: transferUser.value, transferReason: model.transferReason });
    toast.success("已转交");
    return;
  }
  await flowApi.handle(id, {
    action: model.action,
    comment: model.comment,
    rejectToNodeOrder: model.rejectToNodeOrder || undefined,
  });
  toast.success(model.action === "REJECT" ? "已退回" : "已通过");
}

async function revoke(instanceNo: string) {
  try {
    await confirm({
      title: "撤销流程",
      message: "撤销后未完成的待办会关闭。",
      action: async () => {
        await flowApi.revoke(instanceNo);
      },
    });
    toast.success("已撤销");
    await load();
  } catch {
    /* 取消 */
  }
}

function slaClass(row: Row) {
  if (row.slaLevel === "timeout" || row.isTimeout) return "timeout";
  if (row.slaLevel === "warn") return "warn";
  return "";
}

watch(tab, () => {
  pageNo.value = 1;
  void load();
});

onMounted(async () => {
  await load();
  const taskId = String(route.query.taskId || "");
  if (!taskId) return;
  const found = rows.value.find((row) => String(row.id) === taskId);
  if (found) openHandle(found);
  else {
    const data = await flowApi.myTodo({ pageNo: 1, pageSize: 100 });
    const row = (data.list || []).find((item) => String(item.id) === taskId);
    if (row) openHandle(row);
  }
});
</script>

<template>
  <section>
    <PageHeader title="我的流程" sub-title="待办、我发起的和已处理" :show-scope="false" />
    <AppTabs
      v-model:active="tab"
      :items="[
        { key: 'todo', label: '我的待办', count: badge },
        { key: 'initiated', label: '我发起的' },
        { key: 'handled', label: '我已处理' },
      ]"
    />
    <QueryBar v-model="query" :fields="fields" @search="search" @reset="search" />
    <DataTable :columns="columns" :data="rows" :loading="loading" @retry="load">
      <template #cell-slaDeadline="{ row }">
        <span :class="slaClass(row)">{{ row.slaDeadline || "—" }}</span>
      </template>
    </DataTable>
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load" />
    <DetailDrawer v-model:open="detailOpen" title="流程详情" size="L">
      <p>实例 {{ detail?.instanceNo }} · {{ detail?.templateName }}</p>
      <p>发起人 {{ detail?.initiatorName }}</p>
      <pre class="form">{{ detail?.formData }}</pre>
      <h3>流转轨迹</h3>
      <ul>
        <li v-for="(item, index) in (detail?.traceLog as Row[]) || []" :key="index">
          {{ item.actedAt }} {{ item.nodeName }} {{ item.assigneeName }} {{ item.comment }}
        </li>
      </ul>
      <h3>抄送</h3>
      <ul>
        <li v-for="(item, index) in (detail?.ccRecords as Row[]) || []" :key="index">{{ item.ccToName }} {{ item.notifiedAt }}</li>
      </ul>
    </DetailDrawer>
    <FormDrawer v-model:open="handleOpen" title="处理任务" :model="handleForm" :submit="submitHandle" @saved="load">
      <label>动作
        <select v-model="handleForm.action">
          <option value="APPROVE">通过</option>
          <option value="REJECT">退回</option>
          <option value="TRANSFER">转交</option>
        </select>
      </label>
      <label v-if="handleForm.action !== 'TRANSFER'">意见<textarea v-model="handleForm.comment" maxlength="512" /></label>
      <label v-if="handleForm.action === 'REJECT'">退回节点顺序<input v-model="handleForm.rejectToNodeOrder" placeholder="默认发起节点" /></label>
      <template v-if="handleForm.action === 'TRANSFER'">
        <UserSelect v-model="transferUser" />
        <label>原因<textarea v-model="handleForm.transferReason" maxlength="512" /></label>
      </template>
      <Perm code="ims:flow:task:handle" />
    </FormDrawer>
  </section>
</template>

<style scoped>
.timeout { color: var(--red, #c45656); }
.warn { color: var(--orange, #d48806); }
.form { white-space: pre-wrap; }
label { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
</style>
