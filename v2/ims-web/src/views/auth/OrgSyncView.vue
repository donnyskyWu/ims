<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import StatCard, { type StatItem } from "@/components/StatCard.vue";
import AppTabs from "@/components/AppTabs.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import AppModal from "@/components/AppModal.vue";
import ExportButton from "@/components/ExportButton.vue";
import Perm from "@/components/Perm.vue";
import { call } from "@/api/generated/endpoints";
import { toast } from "@/utils/toast";
import { BizError } from "@/api/http";

const route = useRoute();
const router = useRouter();
const tab = ref("diffs");
const metrics = ref<Record<string, unknown>>({});
const summary = ref<Record<string, number>>({});
const rows = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(10);
const loading = ref(false);
const query = ref<Record<string, unknown>>({ keyword: "", category: "OVERRIDE" });
const eventOpen = ref(false);
const eventDetail = ref<Record<string, unknown> | null>(null);
const userOpen = ref(false);
const userDetail = ref<Record<string, unknown> | null>(null);
const replayOpen = ref(false);
const replayForm = ref<Record<string, unknown>>({ startTime: "", endTime: "", statuses: "DEAD" });
const replayCount = ref<number | null>(null);
const batchId = ref("");

const tabs = [
  { key: "diffs", label: "同步差异" },
  { key: "events", label: "同步事件" },
  { key: "batches", label: "对账报告" },
];

const cards = computed<StatItem[]>(() => [
  { title: "在职人员", value: num(metrics.value.userTotal) },
  { title: "昨日事件", value: num(metrics.value.yesterdayEventCount) },
  { title: "待处理", value: num(metrics.value.pendingEventCount), desc: `死信 ${num(metrics.value.deadEventCount)}` },
  { title: "24小时成功率", value: metrics.value.successRate24h === null || metrics.value.successRate24h === undefined ? null : num(metrics.value.successRate24h), format: "percent" },
]);

const fields = computed<QueryField[]>(() => {
  if (tab.value === "events") return [{ key: "keyword", label: "姓名 / 工号 / 事件", type: "input" }];
  if (tab.value === "batches") return [{ key: "keyword", label: "关键字", type: "input" }];
  return [
    { key: "category", label: "差异类别", type: "select", options: [
      { label: "被覆盖", value: "OVERRIDE" },
      { label: "待分配", value: "PENDING_ASSIGN" },
      { label: "本地孤儿", value: "LOCAL_ORPHAN" },
      { label: "同名部门", value: "SAME_NAME" },
      { label: "未绑定", value: "UNBOUND" },
    ] },
    { key: "keyword", label: "关键字", type: "input" },
  ];
});

const columns = computed<TableColumn[]>(() => {
  if (tab.value === "events") {
    return [
      { key: "bizType", label: "类型" },
      { key: "subjectName", label: "人员" },
      { key: "status", label: "状态", type: "status", dictType: "dict_org_sync_status" },
      { key: "eventTime", label: "事件时间", type: "time" },
      { key: "ops", label: "操作", type: "actions", actions: [
        { label: "详情", onClick: (row) => void openEvent(row) },
        { label: "重试", perm: "ims:system:org-sync:run", onClick: (row) => void retry(row) },
      ] },
    ];
  }
  if (tab.value === "batches") {
    return [
      { key: "startedAt", label: "开始", type: "time" },
      { key: "triggerType", label: "触发" },
      { key: "status", label: "状态", type: "status", dictType: "dict_reconcile_status" },
      { key: "diffCount", label: "差异", type: "number" },
      { key: "ops", label: "操作", type: "actions", actions: [{ label: "明细", onClick: (row) => void openBatch(row) }] },
    ];
  }
  return [
    { key: "deptName", label: "部门" },
    { key: "nickname", label: "人员" },
    { key: "field", label: "字段" },
    { key: "beforeValue", label: "变更前" },
    { key: "afterValue", label: "变更后" },
    { key: "ops", label: "操作", type: "actions", actions: [{ label: "人员", onClick: (row) => void openUser(row) }] },
  ];
});

function num(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

async function loadMetrics() {
  metrics.value = await call("sync_metrics_admin_api_ims_auth_org_sync_metrics_get", { silent: true });
  summary.value = await call("diff_summary_admin_api_ims_auth_org_diffs_summary_get", { silent: true });
}

async function load() {
  loading.value = true;
  try {
    if (tab.value === "events") {
      const data = await call<{ list: Record<string, unknown>[]; total: number }>("event_page_admin_api_ims_auth_org_events_get", {
        query: { pageNo: pageNo.value, pageSize: 10, keyword: query.value.keyword },
        silent: true,
      });
      rows.value = data.list || [];
      total.value = Number(data.total || 0);
      return;
    }
    if (tab.value === "batches") {
      const data = await call<{ list: Record<string, unknown>[]; total: number }>("batch_page_admin_api_ims_auth_org_reconcile_batches_get", {
        query: { pageNo: pageNo.value, pageSize: 10 },
        silent: true,
      });
      rows.value = data.list || [];
      total.value = Number(data.total || 0);
      return;
    }
    const data = await call<{ list: Record<string, unknown>[]; total: number }>("diff_page_admin_api_ims_auth_org_diffs_get", {
      query: { pageNo: pageNo.value, pageSize: 10, category: query.value.category || "OVERRIDE", keyword: query.value.keyword },
      silent: true,
    });
    rows.value = data.list || [];
    total.value = Number(data.total || 0);
  } finally {
    loading.value = false;
  }
}

async function openEvent(row: Record<string, unknown>) {
  eventDetail.value = await call("event_detail_admin_api_ims_auth_org_events__ident__get", { pathParams: { ident: String(row.id) }, inDrawer: true });
  eventOpen.value = true;
}

async function openUser(row: Record<string, unknown>) {
  const ident = row.id || row.subjectUserId;
  if (!ident) return;
  userDetail.value = await call("user_detail_admin_api_ims_auth_org_users__ident__get", { pathParams: { ident: String(ident) }, inDrawer: true });
  userOpen.value = true;
}

async function openBatch(row: Record<string, unknown>) {
  batchId.value = String(row.id);
  const data = await call<{ list: Record<string, unknown>[] }>("batch_items_admin_api_ims_auth_org_reconcile_batches__ident__items_get", {
    pathParams: { ident: String(row.id) },
    query: { pageNo: 1, pageSize: 20 },
    inDrawer: true,
  });
  rows.value = data.list || [];
  tab.value = "batches";
}

async function retry(row: Record<string, unknown>) {
  try {
    await call("event_retry_admin_api_ims_auth_org_events__ident__retry_post", {
      pathParams: { ident: String(row.id) },
      idempotent: true,
      tokenKey: `retry-${row.id}`,
      silent: true,
    });
    toast.success("已重新处理");
    await load();
  } catch (caught) {
    toast.error((caught as BizError).msg || "重试失败");
  }
}

async function reconcile() {
  const data = await call<{ id?: string; batchId?: string }>("org_reconcile_admin_api_ims_system_org_sync_reconcile_post", { silent: true });
  toast.success("对账已完成");
  const ident = data.batchId || data.id;
  if (ident) await router.replace({ query: { ...route.query, batchId: String(ident) } });
  tab.value = "batches";
  await load();
}

async function previewReplay(model: Record<string, unknown>) {
  const data = await call<{ count: number }>("replay_preview_admin_api_ims_auth_org_events_replay_preview_get", {
    query: model,
    silent: true,
  });
  replayCount.value = data.count;
  return data;
}

async function runReplay() {
  await call("replay_events_admin_api_ims_auth_org_events_replay_post", {
    body: replayForm.value,
    idempotent: true,
    tokenKey: "org-replay",
    silent: true,
  });
  toast.success("已提交重放");
  replayOpen.value = false;
  await load();
}

function exportEvents(params: Record<string, unknown>) {
  return call("export_events_admin_api_ims_auth_org_events_export_post", { body: params, silent: true });
}

onMounted(() => {
  void loadMetrics();
  void load();
});
</script>

<template>
  <section>
    <PageHeader title="组织架构同步">
      <template #actions>
        <Perm code="ims:system:org-sync:run">
          <button class="btn btn-pri" type="button" @click="reconcile">手动对账</button>
          <button class="btn btn-sec" type="button" @click="replayOpen = true">重放失败事件</button>
        </Perm>
        <Perm code="ims:system:org-sync:export">
          <ExportButton :export-api="exportEvents" :params="query" />
        </Perm>
      </template>
    </PageHeader>
    <p v-if="metrics.dingtalkUnavailable" class="banner">钉钉暂时不可用，同步会稍后重试。</p>
    <p v-if="metrics.reconcileFailedTwice" class="banner">最近两次对账都失败，请查看对账报告。</p>
    <StatCard :items="cards" />
    <AppTabs v-model:active="tab" :items="tabs" sync-query="tab" @change="pageNo = 1; load()" />
    <p class="muted">差异：覆盖 {{ summary.OVERRIDE || 0 }} · 待分配 {{ summary.PENDING_ASSIGN || 0 }} · 本地孤儿 {{ summary.LOCAL_ORPHAN || 0 }}</p>
    <QueryBar v-model="query" :fields="fields" @search="pageNo = 1; load()" @reset="pageNo = 1; load()" />
    <DataTable :columns="columns" :data="rows" :loading="loading" />
    <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load" />
    <DetailDrawer v-model:open="eventOpen" title="事件详情" size="S">
      <DescriptionList v-if="eventDetail" :items="[
        { label: '事件编号', value: String(eventDetail.eventId || '') },
        { label: '人员', value: String(eventDetail.subjectName || '') },
        { label: '状态', value: String(eventDetail.status || '') },
        { label: '变更前部门', value: String(eventDetail.beforeDeptNames || '') },
        { label: '变更后部门', value: String(eventDetail.afterDeptNames || '') },
      ]" />
    </DetailDrawer>
    <DetailDrawer v-model:open="userOpen" title="人员详情" size="M">
      <DescriptionList v-if="userDetail" :items="[
        { label: '姓名', value: String(userDetail.nickname || '') },
        { label: '工号', value: String(userDetail.empNo || '') },
        { label: '主部门', value: String(userDetail.mainDeptName || '') },
        { label: '数据范围', value: String(userDetail.dataScopeText || '') },
        { label: '菜单数', value: String(userDetail.menuCount ?? '') },
      ]" />
    </DetailDrawer>
    <FormDrawer v-model:open="replayOpen" title="重放失败事件" size="S" :model="replayForm" :submit="previewReplay">
      <label class="fld">开始<input v-model="replayForm.startTime" /></label>
      <label class="fld">结束<input v-model="replayForm.endTime" /></label>
    </FormDrawer>
    <AppModal v-model:open="replayOpen" title="确认重放" :width="520">
      <p v-if="replayCount !== null">将重放 {{ replayCount }} 条事件。</p>
      <template #footer>
        <button class="btn btn-pri" type="button" @click="runReplay">确认重放</button>
      </template>
    </AppModal>
    <p v-if="batchId" class="muted">最近批次 {{ batchId }}</p>
  </section>
</template>

<style scoped>
.banner { background: var(--blue-bg); color: var(--text); padding: 8px 12px; border-radius: var(--r-s); }
section { display: flex; flex-direction: column; gap: 12px; }
</style>
