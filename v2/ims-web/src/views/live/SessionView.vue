<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import StatCard, { type StatItem } from "@/components/StatCard.vue";
import AppTabs from "@/components/AppTabs.vue";
import QueryBar, { type QueryField } from "@/components/QueryBar.vue";
import DataTable, { type TableColumn } from "@/components/DataTable.vue";
import AppPagination from "@/components/AppPagination.vue";
import DetailDrawer from "@/components/DetailDrawer.vue";
import FormDrawer from "@/components/FormDrawer.vue";
import AccountSelect from "@/components/AccountSelect.vue";
import RealNameSelect from "@/components/RealNameSelect.vue";
import UserSelect from "@/components/UserSelect.vue";
import AssetSelect from "@/components/AssetSelect.vue";
import DescriptionList from "@/components/DescriptionList.vue";
import Timeline from "@/components/Timeline.vue";
import MoneyText from "@/components/MoneyText.vue";
import { resourceGet, resourcePage, resourceSend } from "@/api/resource";
import { useAuthStore } from "@/stores/auth";
import { hasPerm } from "@/utils/perm";
import { derived } from "./logic";

const route = useRoute();
const auth = useAuthStore();
const tab = ref(String(route.query.tab || "all"));
const query = ref<Record<string, unknown>>({});
const rows = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const pageNo = ref(1);
const pageSize = ref(20);
const stats = ref<Record<string, unknown>>({});
const detailOpen = ref(false);
const detailTab = ref("base");
const current = ref<Record<string, unknown> | null>(null);
const metrics = ref<Record<string, unknown>>({});
const drawer = ref(false);
const form = ref<Record<string, unknown>>({});
const precheck = ref("");
const roomId = ref("");
const report = ref<Record<string, unknown>>({});

const fields: QueryField[] = [
  { key: "sessionCode", label: "场次编号", type: "input" },
  { key: "platform", label: "平台", type: "dict", dictType: "dict_platform_type" },
  { key: "sessionStatus", label: "状态", type: "dict", dictType: "dict_live_session_status" },
  { key: "riskLevel", label: "风险", type: "dict", dictType: "dict_risk_level" },
];

const columns = computed<TableColumn[]>(() => {
  const base: TableColumn[] = [
    { key: "sessionCode", label: "场次 ID", type: "mono" },
    { key: "date", label: "日期" },
    { key: "platformLabel", label: "平台" },
    { key: "accountName", label: "账号" },
    { key: "topic", label: "主题" },
    { key: "sessionStatusLabel", label: "状态", type: "status", dictType: "dict_live_session_status" },
    { key: "riskLevelLabel", label: "风险" },
  ];
  if (hasPerm(auth, "ims:live:report:finance")) base.push({ key: "gmv", label: "GMV", type: "money" });
  base.push({
    key: "ops",
    label: "操作",
    type: "actions",
    actions: [{ label: "详情", onClick: (row) => openDetail(row) }],
  });
  return base;
});

const cards = computed<StatItem[]>(() => {
  const items: StatItem[] = [
    { title: "今日待开播", value: Number(stats.value.pendingToday || 0), onClick: () => pick("risk") },
    { title: "直播中", value: Number(stats.value.living || 0), onClick: () => filterStatus("LIVE") },
    { title: "待录入(24h)", value: Number(stats.value.overdueEntry || 0), onClick: () => pick("pending") },
  ];
  if (hasPerm(auth, "ims:live:report:finance")) items.push({ title: "本月 GMV(已核准)", value: String(stats.value.monthGmv || "0.00"), format: "money" });
  return items;
});

const reportView = computed(() => (current.value?.report as Record<string, unknown> | undefined) || {});
const numbers = computed(() =>
  derived(num(report.value.gmv), num(report.value.orderCount), num(report.value.viewerCount), num(report.value.adCost)),
);

function num(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  return Number(value);
}

function filterStatus(status: string) {
  query.value = { ...query.value, sessionStatus: status };
  void load();
}

function pick(next: string) {
  tab.value = next;
  void load();
}

async function load() {
  const params: Record<string, unknown> = { ...query.value, pageNo: pageNo.value, pageSize: pageSize.value };
  if (tab.value === "risk") params.tab = "risk";
  if (tab.value === "pending") {
    const data = await resourcePage<Record<string, unknown>>("/live/report/pending", params);
    rows.value = data.list;
    total.value = data.total;
    return;
  }
  stats.value = await resourceGet("/live/sessions/stats");
  const data = await resourcePage<Record<string, unknown>>("/live/sessions/list", params);
  rows.value = data.list;
  total.value = data.total;
}

async function openDetail(row: Record<string, unknown>, next = "base") {
  current.value = await resourceGet(`/live/sessions/${row.sessionCode}`);
  metrics.value = await resourceGet(`/live/sessions/${row.sessionCode}/metrics`);
  detailTab.value = next;
  roomId.value = "";
  detailOpen.value = true;
}

function openCreate() {
  form.value = { responsibleUserId: String(auth.user?.id || "") };
  precheck.value = "";
  drawer.value = true;
}

async function checkPerson() {
  if (!form.value.realnameId) {
    precheck.value = "";
    return;
  }
  const data = await resourceGet<{ message?: string }>("/live/register/realname-precheck", { realnameId: form.value.realnameId });
  precheck.value = data.message || "";
}

async function saveRegister() {
  const editing = form.value.sessionCode;
  if (editing) return resourceSend("PUT", `/live/register/${editing}`, form.value);
  return resourceSend("POST", "/live/register", form.value, "live-register");
}

async function act(method: string, path: string, body?: unknown) {
  if (!current.value) return;
  current.value = await resourceSend(method, path, body);
}

async function bindRoom() {
  if (!current.value) return;
  current.value = await resourceSend("PUT", `/live/sessions/${current.value.sessionCode}/football-room`, { roomId: roomId.value || null });
  metrics.value = await resourceGet(`/live/sessions/${current.value.sessionCode}/metrics`);
}

async function saveReport(submit: boolean) {
  if (!current.value) return;
  const path = `/live/report/${current.value.sessionCode}`;
  current.value = await resourceGet(`/live/sessions/${current.value.sessionCode}`);
  if (submit) await resourceSend("POST", path, report.value, "live-report");
  else await resourceSend("PUT", path, report.value);
  current.value = await resourceGet(`/live/sessions/${current.value.sessionCode}`);
}

onMounted(load);
</script>

<template>
  <PageHeader title="直播场次">
    <template #actions>
      <button v-perm="'ims:live:session:register'" class="btn btn-pri" type="button" @click="openCreate">新建场次登记</button>
    </template>
  </PageHeader>
  <StatCard :items="cards" />
  <AppTabs v-model:active="tab" :items="[{ key: 'all', label: '全部' }, { key: 'risk', label: '待风控/待放行' }, { key: 'pending', label: '待录入督办' }]" @change="load" />
  <QueryBar v-model="query" :fields="fields" @search="load" />
  <DataTable :columns="columns" :data="rows" />
  <AppPagination v-model:page-no="pageNo" v-model:page-size="pageSize" :total="total" @change="load" />
  <FormDrawer v-model:open="drawer" title="新建场次登记" :model="form" :submit="saveRegister" @saved="load">
    <el-form-item label="直播账号" required><AccountSelect v-model="form.accountId" live-only status="IN_USE" /></el-form-item>
    <el-form-item label="实名人" required>
      <RealNameSelect v-model="form.realnameId" show-cert-warning @update:model-value="checkPerson" />
      <p v-if="precheck" class="danger">{{ precheck }}</p>
    </el-form-item>
    <el-form-item label="责任人" required><UserSelect v-model="form.responsibleUserId" /></el-form-item>
    <el-form-item label="设备" required><AssetSelect v-model="form.assetIds" multiple asset-types="LIVE,SHOOT" status="IN_USE" /></el-form-item>
    <el-form-item label="主题" required><el-input v-model="form.topic" maxlength="256" /></el-form-item>
    <el-form-item label="计划开播" required><el-date-picker v-model="form.planStartTime" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" /></el-form-item>
    <el-form-item label="计划下播" required><el-date-picker v-model="form.planEndTime" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" /></el-form-item>
  </FormDrawer>
  <DetailDrawer v-model:open="detailOpen" :title="String(current?.sessionCode || '场次详情')" size="L" :tabs="[{ key: 'base', label: '基本信息' }, { key: 'risk', label: '风控登记' }, { key: 'live', label: '直播数据' }, { key: 'report', label: '下播与 GMV' }, { key: 'asset', label: '关联' }]">
    <template #base>
      <DescriptionList :items="[{ label: '主题', value: current?.topic }, { label: '平台', value: current?.platformLabel }, { label: '账号', value: current?.accountName }, { label: '责任人', value: current?.responsibleName }, { label: '状态', value: current?.sessionStatusLabel }]" />
      <Timeline :items="((current?.timeline as { title: string; time: string; detail?: string }[]) || []).map((item) => ({ title: item.title, time: item.time, detail: item.detail || '' }))" />
    </template>
    <template #risk>
      <p>风险分 {{ current?.riskScore }} {{ current?.riskLevelLabel }}</p>
      <p>{{ current?.conclusion }}</p>
      <p v-for="item in (current?.checks as Record<string, unknown>[]) || []" :key="String(item.item)">{{ item.itemLabel }} {{ item.resultLabel }} {{ item.detail }}</p>
      <button v-if="(current?.actions as Record<string, boolean> | undefined)?.start" class="btn btn-pri" type="button" @click="act('PUT', `/live/register/${current?.sessionCode}/start`, {})">确认开播</button>
      <button v-if="(current?.actions as Record<string, boolean> | undefined)?.approve" class="btn btn-pri" type="button" @click="act('PUT', `/live/register/${current?.sessionCode}/approve`, { approve: true, opinion: '同意放行' })">审批放行</button>
      <button v-if="(current?.actions as Record<string, boolean> | undefined)?.rerun" class="btn btn-sec" type="button" @click="act('POST', `/live/register/${current?.sessionCode}/risk-check`)">重新风控</button>
      <a v-if="String((current?.checks as Record<string, unknown>[] | undefined)?.find((item) => item.item === 'CERT_VALID')?.result) === 'FAIL'" href="/ims/corp/resource/certificate">去换证</a>
    </template>
    <template #live>
      <p>{{ metrics.message || metrics.empty || metrics.hint }}</p>
      <el-input v-model="roomId" maxlength="20" placeholder="Football 房间编号" />
      <button v-perm="'ims:live:football:bind'" class="btn btn-pri" type="button" @click="bindRoom">绑定</button>
      <button v-perm="'ims:live:football:bind'" class="btn btn-sec" type="button" @click="act('POST', `/live/sessions/${current?.sessionCode}/football-sync`, { force: true })">从 Football 同步</button>
    </template>
    <template #report>
      <el-form-item label="GMV"><el-input v-model="report.gmv" /></el-form-item>
      <el-form-item label="订单数"><el-input v-model="report.orderCount" /></el-form-item>
      <el-form-item label="观看人数"><el-input v-model="report.viewerCount" /></el-form-item>
      <el-form-item label="峰值在线"><el-input v-model="report.peakOnline" /></el-form-item>
      <el-form-item label="涨粉数"><el-input v-model="report.newFans" /></el-form-item>
      <el-form-item label="退款额"><el-input v-model="report.refundAmount" /></el-form-item>
      <el-form-item label="投放成本"><el-input v-model="report.adCost" /></el-form-item>
      <p>客单价 {{ numbers.unitPrice || "—" }}　UV 价值 {{ numbers.uvValue || "—" }}　ROAS {{ numbers.roas || "—" }}</p>
      <MoneyText v-if="reportView.gmv" :value="String(reportView.gmv)" />
      <p v-if="reportView.rechargeHint">{{ reportView.rechargeHint }}</p>
      <button v-perm="'ims:live:report:entry'" class="btn btn-sec" type="button" @click="saveReport(false)">保存草稿</button>
      <button v-perm="'ims:live:report:entry'" class="btn btn-pri" type="button" @click="saveReport(true)">提交</button>
      <button v-if="(current?.actions as Record<string, boolean> | undefined)?.end" class="btn btn-sec" type="button" @click="act('PUT', `/live/register/${current?.sessionCode}/end`, {})">确认下播</button>
    </template>
    <template #asset>
      <p v-for="item in (current?.devices as Record<string, unknown>[]) || []" :key="String(item.id)">{{ item.assetCode }} {{ item.assetName }}</p>
    </template>
  </DetailDrawer>
</template>
